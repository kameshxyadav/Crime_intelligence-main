"""
Iterative multi-agent workflow tests.

MOCKED:  model outputs (scripted FakeRegistry) and Zetaris (FakeData, in-memory).
REAL:    World Model, Scout Intent, H-MEM and Markovian run through Node against temp dirs;
         the deterministic evidence verifier runs unmodified.
Skipped when Node / Nightshift engine modules are unavailable.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.services import investigation_workflow as iw
from app.services.agents import AgentOutputError
from app.services.meterless_engines import HMemService, MarkovianService, ScoutIntentService
from app.services.meterless_service import MeterlessWorldModelService
from app.services.trace_logger import TraceLogger
from tests.fakes import (CCTV_A, CCTV_A_DUP, EMPTY_EV, FOR_A, FOR_B, INC_A, INC_B, INC_C, PLAN_KEYWORDS, REPORT_OK, SKEPTIC_OK,
                         WIT_B, FakeData, FakeRegistry, good_link)

pytestmark = pytest.mark.skipif(
    not shutil.which("node") or not Path(Settings().meterless_engine_dir, "hmem.js").exists(),
    reason="Node or Nightshift engine modules not installed")

EV = {"forensic_reports": [FOR_A, FOR_B], "cctv_reports": [], "witness_reports": [], "newspaper_reports": []}
FINDER_OK = {"links": [good_link()]}
SKEPTIC_ACCEPT = {"review_status": "accepted", "objections": []}
QUERY = "Are the safe burglaries across NORTH and CENTRAL linked by a chisel-tip pry bar?"


@pytest.fixture
def env(tmp_path, monkeypatch):
    cfg = Settings(state_dir=str(tmp_path / "state"), meterless_world_dir=str(tmp_path / "world"), hmem_scope="wf-test",
                   workflow_max_iterations=3, workflow_max_model_calls=24, workflow_time_budget_seconds=300,
                   zetaris_enabled=True)
    monkeypatch.setattr(iw, "TraceLogger", lambda run_id: TraceLogger(run_id, tmp_path / "logs"))

    def build(script, data=None, reported=None, **cfg_over):
        c = cfg.model_copy(update=cfg_over) if cfg_over else cfg
        return iw.InvestigationWorkflow(
            cfg=c, registry=FakeRegistry(script, reported), data_service=data or FakeData([INC_A, INC_B, INC_C], EV),
            world_model=MeterlessWorldModelService(c), scout=ScoutIntentService(c), hmem=HMemService(c), markovian=MarkovianService(c))
    build.cfg, build.tmp = cfg, tmp_path
    return build


def _ops(res, engine):
    return {o["op"] for o in res["engine_operations"] if o["engine"] == engine}


def test_happy_path_uses_all_four_engines_and_four_agents(env):
    wf = env({"planner": [PLAN_KEYWORDS], "finder": [FINDER_OK], "skeptic": [SKEPTIC_OK], "reporter": [REPORT_OK]},
             reported={"skeptic": "nvidia/nemotron-3-ultra-550b-a55b"})
    res = wf.run_investigation(QUERY)
    assert res["run_status"] == "completed" and res["stopping_reason"] == "evidence_sufficient"
    link = res["candidate_links"][0]
    assert link["validation_status"] == "SUPPORTED" and link["independent_source_count"] == 2
    assert [a["agent"] for a in res["agents"]] == ["planner", "finder", "skeptic", "reporter"]
    assert next(a for a in res["agents"] if a["agent"] == "skeptic")["reported_models"] == ["nvidia/nemotron-3-ultra-550b-a55b"]
    assert {"detect"} <= _ops(res, "scout") and {"retrieve"} <= _ops(res, "hmem") and {"validate", "extract_carryover"} <= _ops(res, "markovian")
    kinds = res["integration_status"]["meterless_engines"]["world_model"]["observations_by_kind"]
    assert {"planner_decision", "finder_finding", "skeptic_objection", "verifier_result", "reporter_synthesis", "run_status"} <= set(kinds)
    assert res["memory"]["write"]["stored"] is True            # SUPPORTED link, no high-severity open objection
    assert res["counts"]["sql_queries"] > 0 and res["report"]["facts"][0]["source_ids"] == ["FOR-0001", "FOR-0002"]
    assert "probab" not in res["candidate_links"][0]["confidence_rationale"].lower().replace("not a probability", "")


def test_skeptic_requests_more_evidence_and_planner_retrieves_again(env):
    skeptic1 = {"review_status": "needs_more_evidence", "objections": [
        {"link_id": "LINK-01", "kind": "missing_evidence", "description": "No CCTV places a vehicle at either scene.", "cited_ids": ["FOR-0001"],
         "severity": "medium", "is_missing_evidence_only": True, "requests_retrieval": True, "retrieval_hint": "CCTV near INC-NORTH-0001"}]}
    plan2 = {"action": "retrieve", "rationale": "CCTV needed", "retrieval_requests": [
        {"kind": "related_records", "incident_ids": ["INC-NORTH-0001", "INC-CEN-0002"], "reason": "skeptic asked for CCTV"}]}
    revised = {"links": [good_link(supporting_evidence_ids=["FOR-0001", "FOR-0002", "CCTV-0001"])]}
    data = FakeData([INC_A, INC_B], {**EV, "cctv_reports": []})
    # CCTV only becomes visible on the second retrieval
    original = data.retrieve_supporting_evidence
    state = {"n": 0}

    def late(ids, locs, limit_per_source=10):
        state["n"] += 1
        out = original(ids, locs, limit_per_source)
        if state["n"] >= 2:
            out["cctv_reports"] = [CCTV_A]
        return out
    data.retrieve_supporting_evidence = late
    wf = env({"planner": [PLAN_KEYWORDS, plan2], "finder": [FINDER_OK, revised], "skeptic": [skeptic1, SKEPTIC_ACCEPT], "reporter": [REPORT_OK]}, data=data)
    # the 'related_records' request is new content for the same incidents -> must execute (distinct fingerprint)
    res = wf.run_investigation(QUERY)
    assert res["iterations_used"] == 2 and res["iterations"][0]["next_action"] == "plan_more_retrieval"
    assert res["iterations"][1]["new_evidence"] >= 1
    assert "CCTV-0001" in res["candidate_links"][0]["supporting_evidence_ids"]
    # first-round objection stays visible and closed, not erased
    objs = res["skeptic"]["objections"]
    assert objs[0]["kind"] == "missing_evidence" and objs[0]["open"] is False
    world = res["integration_status"]["meterless_engines"]["world_model"]["observations_by_kind"]
    assert world["finder_finding"] == 2                     # revision recorded as a new observation, not an overwrite


def test_iteration_limit_stops_loop(env):
    ask = {"review_status": "needs_more_evidence", "objections": [
        {"link_id": "LINK-01", "kind": "missing_evidence", "description": "Need more.", "severity": "low", "requests_retrieval": True}]}
    plans = [PLAN_KEYWORDS] + [{"action": "retrieve", "retrieval_requests": [
        {"kind": "location_window", "incident_ids": ["INC-NORTH-0001"], "keywords": [f"k{n}"]}]} for n in range(3)]
    wf = env({"planner": plans, "finder": [FINDER_OK] * 3, "skeptic": [ask] * 3, "reporter": [REPORT_OK]}, workflow_max_iterations=2)
    res = wf.run_investigation(QUERY)
    assert res["iterations_used"] == 2 and res["stopping_reason"] == "iteration_limit_reached"
    assert any(o["open"] for o in res["skeptic"]["objections"])           # unresolved objection is not hidden
    assert any("Need more." in x for x in res["contradictions_and_limitations"])


def test_model_call_budget_stops_with_partial_result(env):
    wf = env({"planner": [PLAN_KEYWORDS], "finder": [FINDER_OK], "skeptic": [SKEPTIC_OK], "reporter": [REPORT_OK]}, workflow_max_model_calls=2)
    res = wf.run_investigation(QUERY)
    assert res["run_status"] == "budget_exhausted" and "budget" in res["stopping_reason"]
    assert res["candidate_incidents"] and res["partial_failures"][0]["component"] == "budget"
    assert res["resume_hint"]


def test_hallucinated_ids_are_rejected_and_never_reach_report_facts(env):
    bad = {"links": [good_link(target_incident_id="INC-HALLUCINATED-0009", supporting_evidence_ids=["FOR-0001", "FOR-9999"])]}
    report = {**REPORT_OK, "facts": [{"statement": "Invented fact", "source_ids": ["FOR-9999"]},
                                     {"statement": "Real fact", "source_ids": ["FOR-0001", "FOR-9999"]}]}
    wf = env({"planner": [PLAN_KEYWORDS, {"action": "conclude"}], "finder": [bad, {"links": [], "withdrawn_link_ids": ["LINK-01"]}],
              "skeptic": [SKEPTIC_ACCEPT], "reporter": [report]})
    res = wf.run_investigation(QUERY)
    assert res["validation_results"][0]["status"] == "UNSUPPORTED" and "INC-HALLUCINATED-0009" in res["validation_results"][0]["rejected_ids"]
    facts = res["report"]["facts"]
    assert len(facts) == 1 and facts[0]["source_ids"] == ["FOR-0001"] and facts[0]["dropped_unknown_ids"] == ["FOR-9999"]
    assert res["report"]["unverified_statements"][0]["statement"] == "Invented fact"
    assert res["memory"]["write"]["attempted"] is False        # nothing unverified is promoted to memory
    assert res["stopping_reason"].startswith("no_supportable_links_found")


def test_reporter_cannot_hide_objections_or_contradictions(env):
    skeptic = {"review_status": "accepted_with_objections", "objections": [
        {"link_id": "LINK-01", "kind": "contradiction", "description": "Witness describes a red sedan but CCTV shows a grey minivan.",
         "cited_ids": ["CCTV-0001", "WIT-0001"], "severity": "high"}]}
    data = FakeData([INC_A, INC_B], {**EV, "cctv_reports": [CCTV_A], "witness_reports": [{**WIT_B, "vehicle_description": "red sedan",
                                                                                         "observation_text": "red sedan"}]})
    link = good_link(supporting_evidence_ids=["FOR-0001", "FOR-0002", "CCTV-0001", "WIT-0001"])
    wf = env({"planner": [PLAN_KEYWORDS], "finder": [{"links": [link]}], "skeptic": [skeptic], "reporter": [{**REPORT_OK, "contradictions_and_limitations": []}]}, data=data)
    res = wf.run_investigation(QUERY)
    text = " ".join(res["contradictions_and_limitations"])
    assert "red sedan" in text and "[skeptic" in text and "vehicle_color_conflict" not in text.replace("[deterministic_verifier]", "") or "grey" in text
    assert any(c["type"] == "vehicle_color_conflict" for c in res["candidate_links"][0]["contradictions"])
    assert res["memory"]["write"]["attempted"] is False        # open high-severity objection blocks promotion to memory


def test_duplicate_reports_do_not_inflate_corroboration(env):
    data = FakeData([INC_A, INC_B], {"forensic_reports": [], "cctv_reports": [CCTV_A, CCTV_A_DUP], "witness_reports": [], "newspaper_reports": []})
    link = good_link(supporting_evidence_ids=["CCTV-0001", "CCTV-0009"], shared_attributes=[])
    wf = env({"planner": [PLAN_KEYWORDS], "finder": [{"links": [link]}], "skeptic": [SKEPTIC_ACCEPT], "reporter": [REPORT_OK]}, data=data)
    res = wf.run_investigation(QUERY)
    v = res["candidate_links"][0]
    assert v["independent_source_count"] == 1 and v["validation_status"] == "WEAK"
    assert res["memory"]["write"]["attempted"] is False


def test_malformed_planner_output_uses_labelled_deterministic_fallback(env):
    wf = env({"planner": [AgentOutputError("planner", "bad json", [])], "finder": [FINDER_OK], "skeptic": [SKEPTIC_ACCEPT], "reporter": [REPORT_OK]})
    res = wf.run_investigation(QUERY)
    assert res["iterations"][0]["planner_fallback"] is True
    assert any(f["component"] == "planner" for f in res["partial_failures"])
    assert res["candidate_incidents"]


def test_finder_failure_blocks_without_fabricating_links(env):
    wf = env({"planner": [PLAN_KEYWORDS], "finder": [AgentOutputError("finder", "bad", [])], "reporter": [REPORT_OK]})
    res = wf.run_investigation(QUERY)
    assert res["run_status"] == "blocked" and res["stopping_reason"] == "finder_failed" and res["candidate_links"] == []


def test_failed_skeptic_review_is_visible_and_blocks_memory_promotion(env):
    wf = env({"planner": [PLAN_KEYWORDS], "finder": [FINDER_OK], "skeptic": [AgentOutputError("skeptic", "bad", [])], "reporter": [REPORT_OK]})
    res = wf.run_investigation(QUERY)
    assert res["skeptic"]["review_status"] == "review_failed"
    assert res["memory"]["write"]["attempted"] is False and "Skeptic" in res["memory"]["write"]["reason"]
    assert any("No Skeptic review completed" in x for x in res["contradictions_and_limitations"])
    assert any(f["component"] == "skeptic" for f in res["partial_failures"])


def test_skeptic_output_variations_are_normalised_not_discarded():
    from app.services.agents import SkepticReview
    r = SkepticReview.model_validate({"review_status": "needs_more_evidence", "suggested_retrieval": [{"query": "CCTV near scene", "priority": "high"}],
                                      "objections": [{"description": "x", "kind": "weird_kind", "severity": "critical", "cited_ids": "FOR-1"}]})
    assert r.objections[0].kind == "other" and r.objections[0].severity == "medium" and r.objections[0].cited_ids == ["FOR-1"]


def test_reporter_failure_yields_labelled_template_report(env):
    wf = env({"planner": [PLAN_KEYWORDS], "finder": [FINDER_OK], "skeptic": [SKEPTIC_ACCEPT], "reporter": [AgentOutputError("reporter", "bad", [])]})
    res = wf.run_investigation(QUERY)
    assert res["report"]["model_generated"] is False and "Template report" in res["executive_summary"]


def test_no_records_found_stops_cleanly(env):
    wf = env({"planner": [PLAN_KEYWORDS]}, data=FakeData([], EMPTY_EV))
    res = wf.run_investigation(QUERY)
    assert res["stopping_reason"] == "no_records_found" and res["candidate_links"] == []


def test_clarify_and_refuse_make_no_model_or_sql_calls(env):
    data = FakeData([INC_A], EV)
    wf = env({}, data=data)
    r1 = wf.run_investigation("pry bar")
    assert r1["run_status"] == "needs_clarification" and r1["counts"]["model_calls"] == 0
    r2 = wf.run_investigation("delete all records in the evidence table")
    assert r2["run_status"] == "refused" and data.query_count == 0
    assert wf._registry.calls == []


def test_unfinished_run_resumes_from_markovian_state(env):
    # Zetaris dies during the second retrieval; incidents already exist so the run is returned as interrupted.
    skeptic1 = {"review_status": "needs_more_evidence", "objections": [
        {"link_id": "LINK-01", "kind": "missing_evidence", "description": "More needed", "severity": "low", "requests_retrieval": True}]}
    plan2 = {"action": "retrieve", "retrieval_requests": [{"kind": "by_incident_ids", "incident_ids": ["INC-RIV-0003"]}]}
    data = FakeData([INC_A, INC_B, INC_C], EV)
    orig = data.get_incidents_by_ids

    def flaky(ids):
        if "INC-RIV-0003" in ids:
            from app.services.zetaris_adapter import ZetarisConnectionError
            raise ZetarisConnectionError("down")
        return orig(ids)
    data.get_incidents_by_ids = flaky
    wf = env({"planner": [PLAN_KEYWORDS, plan2], "finder": [FINDER_OK], "skeptic": [skeptic1], "reporter": [REPORT_OK]}, data=data)
    res = wf.run_investigation(QUERY)
    assert res["run_status"] == "interrupted" and res["resume_hint"] and res["partial_failures"]
    run_id = res["investigation_id"]
    saved = MarkovianService(env.cfg.model_copy(update={})).load(run_id)
    assert saved and saved[0].status == "interrupted" and saved[0].iteration == 2 and saved[0].retrieval_requests

    data.get_incidents_by_ids = orig                         # Zetaris recovers
    wf2 = env({"planner": [{"action": "conclude"}], "finder": [FINDER_OK], "skeptic": [SKEPTIC_ACCEPT], "reporter": [REPORT_OK]}, data=data)
    res2 = wf2.run_investigation("ignored", continue_from=run_id)
    assert res2["investigation_id"] == run_id and res2["intent"] == "CONTINUE_INVESTIGATION"
    assert res2["run_status"] == "completed" and res2["iterations_used"] >= 3
    done = MarkovianService(env.cfg).load(run_id)[0]
    assert done.status == "completed"
    # a completed run cannot be "continued"
    res3 = wf2.run_investigation("x", continue_from=run_id)
    assert res3["run_status"] == "needs_clarification"


def test_trace_file_records_models_engines_sql_without_secrets(env):
    wf = env({"planner": [PLAN_KEYWORDS], "finder": [FINDER_OK], "skeptic": [SKEPTIC_OK], "reporter": [REPORT_OK]})
    res = wf.run_investigation(QUERY)
    lines = (env.tmp / "logs" / res["trace_file"]).read_text().splitlines()
    import json
    events = [json.loads(l) for l in lines]
    assert any(e["action"] == "model_call" and e["provider_meta"]["reported_model"] for e in events)
    assert any(e["action"].startswith("scout.") for e in events) and any(e.get("sql_meta") for e in events)
    assert any(e["agent"] == "verifier" for e in events)
    assert "sk-" not in "".join(lines) and "Bearer" not in "".join(lines)


# ── Sample mode isolation (API level) ───────────────────────────────────────
def test_sample_mode_never_touches_live_services(monkeypatch):
    from app.main import app
    from app.routers import investigations as router

    def boom(*a, **k):
        raise AssertionError("live workflow must not run in sample mode")
    monkeypatch.setattr(router.investigation_workflow, "run_investigation", boom)
    r = TestClient(app).post("/api/investigations/analyze", json={"query": "q", "sample_mode": True, "scenario_id": "crowbar_safe_cracking"})
    body = r.json()
    assert r.status_code == 200 and body["is_sample"] is True and "SAMPLE" in body["data_mode"].upper()
    assert not body.get("engine_operations") and not body.get("model_calls")


def test_truncated_output_triggers_concise_repair_hint():
    from unittest.mock import MagicMock
    from app.services import agents as ag
    from app.services.model_registry import CallRecord
    from app.services.nightshift_client import NightshiftResponse
    cut = NightshiftResponse(content='{"review_status": "accepted", "objections": [', model="m", provider="p", finish_reason="length")
    ok = NightshiftResponse(content='{"review_status": "accepted", "objections": []}', model="m", provider="p", finish_reason="stop")
    reg = MagicMock()
    reg.generate.side_effect = [(cut, CallRecord(role="skeptic", requested_model="m")), (ok, CallRecord(role="skeptic", requested_model="m"))]
    res = ag.call_agent(reg, "skeptic", "s", "u", ag.SkepticReview)
    assert res.repaired and "cut off" in reg.generate.call_args_list[1].args[1][-1]["content"]
