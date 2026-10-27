"""
Meterless Engine adapter tests - LOCAL ENGINE tests.

These execute the REAL engine modules installed with Nightshift.app (scout-intents.js,
hmem.js, markovian.js) through Node, against temp storage. They are not mocks, but they
are also not Meterless's own conformance suites (none ship in the app bundle).
Skipped automatically when Node or Nightshift.app is absent.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.config import Settings
from app.services.meterless_engines import (
    HMemService, MarkovianService, ScoutIntentService, WorkingState, run_engine)

CFG = Settings()
pytestmark = pytest.mark.skipif(
    not shutil.which("node") or not Path(CFG.meterless_engine_dir, "hmem.js").exists(),
    reason="Node or Nightshift engine modules not installed")


def _cfg(tmp_path) -> Settings:
    return Settings(state_dir=str(tmp_path), hmem_scope="test-scope")


# ── Scout Intent ────────────────────────────────────────────────────────────
def test_scout_runs_real_detector():
    r, op = ScoutIntentService(CFG).detect("investigate crowbar burglaries")
    assert op.engine == "scout" and op.status == "ok"
    assert r["mode"] and r["registrySize"] > 100 and r["ms"] < 50


def test_scout_selftest_runs():
    r, op = ScoutIntentService(CFG).selftest()
    assert r["maxMs"] < 16 and op.status == "ok"


@pytest.mark.parametrize("query,kwargs,intent", [
    ("Find cross-station burglary patterns involving a pry bar", {}, "CROSS_STATION_SEARCH"),
    ("Compare INC-NORTH-0042 and INC-CEN-0118", {}, "COMPARE_INCIDENTS"),
    ("Are INC-NORTH-0042 and INC-CEN-0118 related to the same series?", {}, "INVESTIGATE_RELATIONSHIP"),
    ("Review contradictions in the witness statements for the safe burglaries", {}, "REVIEW_CONTRADICTIONS"),
    ("Continue the investigation", {"continue_from": "inv_1793018897_06c2db"}, "CONTINUE_INVESTIGATION"),
    ("pry bar", {}, "CLARIFY"),
])
def test_routing_intents(query, kwargs, intent):
    route, op = ScoutIntentService(CFG).route(query, **kwargs)
    assert route.intent == intent and route.scout["mode"] and op.status == "ok"


def test_routing_validates_arguments_before_anything_runs():
    svc = ScoutIntentService(CFG)
    r, _ = svc.route("compare these", incident_ids=["INC-NORTH-0042", "DROP TABLE x"])
    assert r.intent == "CLARIFY" and "Invalid incident" in r.clarification
    r, _ = svc.route("search burglaries", station_ids=["MARS"])
    assert r.intent == "CLARIFY" and "Unknown station" in r.clarification
    r, _ = svc.route("search burglaries", date_from="yesterday")
    assert r.intent == "CLARIFY"
    r, _ = svc.route("continue", continue_from="../../etc/passwd")
    assert r.intent == "CLARIFY"


def test_routing_refuses_data_mutation_and_never_executes():
    r, _ = ScoutIntentService(CFG).route("delete all records in the incidents table")
    assert r.intent == "REFUSE" and r.refusal


def test_destructive_vocabulary_in_a_crime_query_is_not_refused():
    r, _ = ScoutIntentService(CFG).route("Find incidents where offenders destroyed CCTV cameras before burglary")
    assert r.intent == "CROSS_STATION_SEARCH"


# ── H-MEM ───────────────────────────────────────────────────────────────────
def test_hmem_roundtrip_with_provenance_and_scope_wall(tmp_path):
    h = HMemService(_cfg(tmp_path))
    stored, op = h.store_verified_summary(
        "Chisel pry bar safe burglaries NORTH CENTRAL",
        "Lead (unadjudicated): INC-NORTH-0042 and INC-CEN-0118 share a 36mm chisel-tip tool per FOR-0089.",
        0.8, "nvidia/nemotron-3.5-lightning-30b-a3b", "rcpt_1", ["FOR-0089"])
    assert stored and op.detail["audit"][0]["action"] == "create"
    hits, _ = h.retrieve("chisel pry bar safe burglaries across NORTH and CENTRAL")
    assert hits and hits[0]["source"]["model"] == "nvidia/nemotron-3.5-lightning-30b-a3b"
    assert hits[0]["source"]["receiptId"] == "rcpt_1" and hits[0]["scope"] == "test-scope"
    other = HMemService(Settings(state_dir=str(tmp_path), hmem_scope="another-scope"), store_file=tmp_path / "hmem-knowledge.json")
    assert other.retrieve("chisel pry bar safe burglaries across NORTH and CENTRAL")[0] == []


def test_hmem_refuses_low_confidence_and_secrets(tmp_path):
    h = HMemService(_cfg(tmp_path))
    ok, _ = h.store_verified_summary("q about burglaries", "A sufficiently long unverified hypothesis about a burglary series.", 0.3, "m", None, [])
    assert ok is False                                    # below H-MEM's own confidence floor
    ok, _ = h.store_verified_summary("q about keys", "The api_key: sk-abcdefghijklmnopqrstuvwxyz was found at the scene.", 0.9, "m", None, [])
    assert ok is False                                    # H-MEM's secret write-gate
    assert h.stats()[0]["records"] == 0


# ── Markovian ───────────────────────────────────────────────────────────────
def test_markovian_validates_config_and_clamps_iterations():
    m = MarkovianService(Settings(workflow_max_iterations=99))
    cfg, op = m.validate()
    assert cfg["maxChunks"] == 32 and op.status == "ok"


def test_markovian_rejects_invalid_config():
    from app.services.meterless_engines import EngineUnavailableError
    with pytest.raises(EngineUnavailableError):
        run_engine(CFG, "markovian", "validate", {"config": {"chunkSize": 1000, "carryoverTokens": 800}})


def test_markovian_carryover_is_compact_and_uses_marker_rung():
    m = MarkovianService(CFG)
    st = WorkingState(run_id="inv_1_aaaaaa", objective="o", intent="CROSS_STATION_SEARCH", iteration=2,
                      completed_steps=["i1:retrieved 6 inc/40 ev"], validated_findings=[
                          {"link_id": "LINK-01", "status": "WEAK", "source_incident_id": "INC-NORTH-0001", "target_incident_id": "INC-CEN-0002"}],
                      skeptic_objections=[{"kind": "timeline", "description": "x" * 500, "open": True}],
                      evidence_refs={"evidence": [f"FOR-{i:04d}" for i in range(500)]}, outstanding_tasks=["fetch CCTV"])
    carry, op = m.checkpoint(st)
    assert op.detail["strategy"] == "marker" and "LINK-01:WEAK" in carry
    assert len(carry) < 3200 and "FOR-0499" not in carry      # bounded: evidence held by reference, capped
    frame, _ = m.continuation_prompt("A very long goal " * 40, carry)
    assert "RESEARCH STATE" in frame and len(frame) < 4500    # no history replay


def test_markovian_state_resumes_from_disk(tmp_path):
    m = MarkovianService(_cfg(tmp_path))
    st = WorkingState(run_id="inv_1793018897_06c2db", objective="obj", intent="COMPARE_INCIDENTS", iteration=2, status="interrupted",
                      retrieval_requests=[{"kind": "by_incident_ids", "incident_ids": ["INC-NORTH-0001"]}])
    m.save(st, "COMPLETED: x")
    loaded, carry = m.load("inv_1793018897_06c2db")
    assert loaded.iteration == 2 and loaded.status == "interrupted" and loaded.retrieval_requests[0]["kind"] == "by_incident_ids"
    assert carry == "COMPLETED: x" and m.load("inv_1793018897_aaaaaa") is None
    with pytest.raises(ValueError):
        m.load("../evil")


def test_engines_health_endpoint_runs_one_real_operation_per_engine():
    from fastapi.testclient import TestClient
    from app.main import app
    body = TestClient(app).get("/api/engines/health").json()
    assert {"world_model", "scout_intent", "h_mem", "markovian"} <= set(body)
    assert body["scout_intent"]["status"] == "connected" and body["markovian"]["status"] == "connected"
