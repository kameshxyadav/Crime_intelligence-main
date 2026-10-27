"""
LIVE integration tests - real Zetaris SQL, real Nightshift model calls, real Meterless engines.

Opt-in:  RUN_LIVE_TESTS=1 python -m pytest -m live -v     (a full investigation takes ~3-6 minutes)

Nothing here is mocked. Model output is non-deterministic, so these tests assert structural guarantees
(provenance, grounding, trace content, engine operations) rather than a particular conclusion.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from app.config import settings
from app.services.meterless_engines import HMemService, MarkovianService, ScoutIntentService
from app.services.meterless_service import meterless_service
from app.services.model_registry import ModelRegistry
from app.services.nightshift_client import NightshiftClient
from app.services.zetaris_investigation_service import ZetarisInvestigationService

pytestmark = [pytest.mark.live, pytest.mark.skipif(os.getenv("RUN_LIVE_TESTS") != "1", reason="set RUN_LIVE_TESTS=1 to run live tests")]

LIGHTNING = "nvidia/nemotron-3.5-lightning-30b-a3b"
ULTRA = "nvidia/nemotron-3-ultra-550b-a55b"
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def client() -> NightshiftClient:
    if not settings.nightshift_configured:
        pytest.skip("Nightshift not configured")
    return NightshiftClient(settings)


@pytest.fixture(scope="module")
def zetaris() -> ZetarisInvestigationService:
    if not settings.zetaris_configured:
        pytest.skip("Zetaris not configured")
    return ZetarisInvestigationService(settings)


def test_live_nightshift_lightning_reports_real_model(client):
    r = client.generate([{"role": "user", "content": "Reply with the single word ONLINE"}], model=LIGHTNING, max_tokens=20)
    assert r.content.strip() and "nemotron" in r.model.lower() and r.provider


def test_live_registry_verifies_models_against_nightshift_catalogue(client):
    reg = ModelRegistry(settings, client)
    rep = reg.report(probe=True)
    assert rep["catalog_checked"] is True
    assert rep["roles"]["planner"]["effective_model"] == LIGHTNING
    # Reported state must match what Nightshift lists - never assumed.
    listed = set(reg.catalog() or [])
    for role in ("skeptic", "embedding"):
        a = rep["roles"][role]
        if a["configured_model"] and a["configured_model"] not in listed:
            assert a["status"] in ("fallback", "unavailable")
    assert rep["roles"]["rerank"]["status"] == "unavailable"


def test_live_ultra_skeptic_model_answers_when_listed(client):
    if ULTRA not in (ModelRegistry(settings, client).catalog() or []):
        pytest.skip("Ultra not listed by Nightshift")
    reg = ModelRegistry(settings, client)
    resp, rec = reg.generate("skeptic", [{"role": "user", "content": "Give one reason two burglaries with similar tool marks may be unrelated. One sentence."}],
                             max_tokens=120)
    assert resp.content.strip() and rec.reported_model == ULTRA and not rec.fallback_used


def test_live_zetaris_sql_returns_provenance_fields(zetaris):
    truth = json.loads((ROOT / "data/evaluation/ground_truth.json").read_text())[0]["incident_ids"]
    rows = zetaris.get_incidents_by_ids(truth)
    assert {r["incident_id"] for r in rows} == set(truth)
    assert all(r["station_id"] and r["data_quality"] for r in rows)
    ev = zetaris.retrieve_supporting_evidence(truth, [r["location_id"] for r in rows], 5)
    assert any(ev[k] for k in ev) and zetaris.query_count >= 2 and not zetaris.errors


def test_live_world_model_roundtrip():
    run_id = f"live_{int(time.time())}"
    meterless_service.init_investigation_state(run_id, "live test", ["NORTH"])
    meterless_service.record_finder_link(run_id, 1, {"link_id": "L1", "source_incident_id": "INC-NORTH-0042", "target_incident_id": "INC-CEN-0118"})
    meterless_service.record_finder_link(run_id, 2, {"link_id": "L1", "source_incident_id": "INC-NORTH-0042", "target_incident_id": "INC-CEN-0118"})
    st = meterless_service.get_investigation_state(run_id)
    assert len(st["finder_findings"]) == 2             # revisions preserved as separate observations


def test_live_hmem_scout_markovian_operations(tmp_path):
    from app.config import Settings
    cfg = Settings(state_dir=str(tmp_path))
    route, op = ScoutIntentService(cfg).route("Compare INC-NORTH-0042 and INC-CEN-0118")
    assert op.status == "ok" and route.intent == "COMPARE_INCIDENTS"
    stored, _ = HMemService(cfg).store_verified_summary("live memory probe about burglaries", "Lead (unadjudicated): INC-NORTH-0042 ~ INC-CEN-0118 per FOR-0089 toolmark.", 0.8, "m", None, ["FOR-0089"])
    assert stored
    _, mop = MarkovianService(cfg).validate()
    assert mop.status == "ok"


def test_live_complete_investigation_with_real_evidence():
    from app.services.investigation_workflow import InvestigationWorkflow
    truth = json.loads((ROOT / "data/evaluation/ground_truth.json").read_text())[0]["incident_ids"][:2]
    wf = InvestigationWorkflow(settings)
    res = wf.run_investigation(f"Are incidents {truth[0]} and {truth[1]} related to one another?", incident_ids=truth)
    assert res["run_status"] in ("completed", "budget_exhausted") and res["counts"]["sql_queries"] > 0
    assert {i["incident_id"] for i in res["candidate_incidents"]} >= set(truth)
    called = {a["agent"] for a in res["agents"]}
    assert {"planner", "finder", "reporter"} <= called
    assert all(a["reported_models"] for a in res["agents"])           # every agent records the model that answered
    ops = {(o["engine"], o["op"]) for o in res["engine_operations"]}
    assert ("scout", "detect") in ops and ("markovian", "validate") in ops and ("hmem", "retrieve") in ops
    wm = res["integration_status"]["meterless_engines"]["world_model"]["observations_by_kind"]
    assert wm.get("planner_decision") and wm.get("finder_finding")
    for l in res["candidate_links"]:                                   # every verified citation exists in Zetaris data
        retrieved = {r.get(k) for rows in res["supporting_evidence"].values() for r in rows
                     for k in ("evidence_report_id", "evidence_item_id", "cctv_report_id", "witness_report_id", "news_id")}
        assert set(l["supporting_evidence_ids"]) <= retrieved
    trace = (ROOT / "logs" / res["trace_file"]).read_text()
    assert "model_call" in trace and "zetaris_sql" in trace and "Bearer" not in trace
