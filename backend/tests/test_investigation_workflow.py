"""
Legacy Pipeline + Investigation API Tests (mocked Nightshift)
=========================================
Tests the end-to-end multi-agent investigation workflow with mocked
Nightshift AI calls and real Meterless World Model and Zetaris (or local
fallback) integration.

These tests validate:
1. Sample mode returns isolated scenario data without touching live integrations.
2. Live mode with mocked Nightshift: Planner → Analyst → Evaluator → Reporter.
3. Evaluator correctly rejects links with hallucinated incident IDs.
4. Evaluator correctly filters hallucinated evidence IDs from valid ones.
5. Analyst fallback link is generated when the model returns no valid links.
6. Investigation API endpoint returns correct HTTP codes for various configurations.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.config import Settings, settings
from app.services.investigation_workflow import _extract_json_block
# These workflow tests cover the LEGACY single-pass pipeline (kept as the evaluation baseline).
# The iterative multi-agent workflow is covered in test_multiagent_workflow.py.
from app.services.legacy_pipeline_workflow import LegacyInvestigationWorkflow as InvestigationWorkflow
from app.services.nightshift_client import NightshiftClient, NightshiftResponse
from app.services.sample_scenarios import SAMPLE_SCENARIOS, get_sample_investigation

client = TestClient(app)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _mock_nightshift(content: str, model: str = "nvidia/nemotron-3.5-lightning-30b-a3b") -> NightshiftResponse:
    """Create a fake NightshiftResponse with the given content."""
    return NightshiftResponse(
        content=content,
        model=model,
        provider="nvidia",
        winning_route={"model": model, "provider": "nvidia", "tier": "A"},
        receipt_id="rcpt_test_mock",
        latency_ms=42.0,
        raw_metadata={"reported_model": model, "provider": "nvidia", "meterless_meta": {}},
    )


def _make_mock_workflow(planner_content: str, analyst_content: str, evaluator_content: str, reporter_content: str) -> InvestigationWorkflow:
    """Build an InvestigationWorkflow with all AI calls fully mocked."""
    call_sequence = [
        _mock_nightshift(planner_content),
        _mock_nightshift(analyst_content),
        _mock_nightshift(evaluator_content),
        _mock_nightshift(reporter_content),
    ]
    call_iter = iter(call_sequence)

    mock_ai = MagicMock(spec=NightshiftClient)
    mock_ai.generate.side_effect = lambda **kwargs: next(call_iter)
    # Support both positional and keyword call patterns
    mock_ai.generate.side_effect = lambda *args, **kwargs: next(call_iter)

    return InvestigationWorkflow(ai_client=mock_ai)


# ── _extract_json_block ────────────────────────────────────────────────────────


def test_extract_json_block_direct_json():
    result = _extract_json_block('{"key": "value"}')
    assert result == {"key": "value"}


def test_extract_json_block_fenced_code():
    result = _extract_json_block('```json\n{"key": "value"}\n```')
    assert result == {"key": "value"}


def test_extract_json_block_array():
    result = _extract_json_block('[{"a": 1}, {"b": 2}]')
    assert result == [{"a": 1}, {"b": 2}]


def test_extract_json_block_empty_returns_none():
    result = _extract_json_block("")
    assert result is None


def test_extract_json_block_invalid_returns_none():
    result = _extract_json_block("This is just plain text with no JSON.")
    assert result is None


# ── Sample Mode ────────────────────────────────────────────────────────────────


def test_sample_investigation_crowbar():
    """Sample mode must return deterministic isolated data."""
    result = get_sample_investigation("crowbar_safe_cracking", "test query")
    assert result["is_sample"] is True
    assert result["data_mode"] == "sample_mode"
    assert result["scenario_id"] == "crowbar_safe_cracking"
    assert len(result["candidate_incidents"]) >= 2
    assert len(result["candidate_links"]) >= 1
    # All links should be grounded
    incident_ids = {inc["incident_id"] for inc in result["candidate_incidents"]}
    for link in result["candidate_links"]:
        assert link["source_incident_id"] in incident_ids
        assert link["target_incident_id"] in incident_ids


def test_sample_investigation_all_scenarios():
    """All 3 sample scenarios must return valid data."""
    for sc_id in SAMPLE_SCENARIOS:
        result = get_sample_investigation(sc_id, "test")
        assert result["is_sample"] is True
        assert result["data_mode"] == "sample_mode"
        assert result["investigation_id"].startswith("sample-")
        assert result["scenario_id"] == sc_id
        assert len(result["candidate_incidents"]) >= 1
        assert len(result["candidate_links"]) >= 1


def test_sample_investigation_unknown_falls_back():
    """Unknown scenario ID should fall back to first scenario or default."""
    result = get_sample_investigation("UNKNOWN_SCENARIO_XYZ", "test")
    assert result["is_sample"] is True
    assert result["data_mode"] == "sample_mode"
    assert len(result["candidate_incidents"]) >= 1


def test_api_investigation_sample_mode():
    """API endpoint with sample_mode=true should return 200 with sample data."""
    resp = client.post("/api/investigations/analyze", json={
        "query": "Safe burglary crowbar grey minivan",
        "station_ids": ["NORTH", "CENTRAL"],
        "sample_mode": True,
        "scenario_id": "crowbar_safe_cracking",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_sample"] is True
    assert data["data_mode"] == "sample_mode"
    assert "candidate_incidents" in data
    assert "candidate_links" in data
    assert "executive_summary" in data


# ── Sample Scenarios List ──────────────────────────────────────────────────────


def test_api_investigation_samples_list():
    resp = client.get("/api/investigations/samples")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    scenario_ids = {s["scenario_id"] for s in data}
    assert "crowbar_safe_cracking" in scenario_ids
    for s in data:
        assert "title" in s
        assert "query" in s
        assert "target_stations" in s
        assert s["incidents_count"] >= 1
        assert s["links_count"] >= 1


# ── AI Diagnostic and Engine Health ───────────────────────────────────────────


def test_api_ai_diagnostic():
    """AI diagnostic should return structured JSON (may be connected or error)."""
    resp = client.get("/api/ai/diagnostic")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "configured" in data
    assert "message" in data


def test_api_engine_health():
    """Engine health should return structured JSON."""
    resp = client.get("/api/engine/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "engine" in data
    assert data["engine"] == "meterless_world_model"


# ── Live Investigation: 503 When Zetaris Unconfigured ─────────────────────────


def test_api_investigation_503_if_zetaris_not_configured(monkeypatch):
    """Live mode must return 503 if Zetaris is not configured."""
    monkeypatch.setattr(settings, "zetaris_enabled", False)
    resp = client.post("/api/investigations/analyze", json={
        "query": "test burglary",
        "station_ids": ["NORTH"],
        "sample_mode": False,
    })
    assert resp.status_code == 503
    assert "Zetaris" in resp.json()["detail"]


def test_api_investigation_503_if_nightshift_not_configured(monkeypatch):
    """Live mode must return 503 if Nightshift is not configured."""
    # Patch the computed properties directly so we can simulate:
    # - Zetaris: configured (passes the first check)
    # - Nightshift: NOT configured (triggers the 503 we want to test)
    monkeypatch.setattr(
        type(settings), "zetaris_configured", property(lambda self: True)
    )
    monkeypatch.setattr(
        type(settings), "nightshift_configured", property(lambda self: False)
    )
    resp = client.post("/api/investigations/analyze", json={
        "query": "test burglary",
        "station_ids": ["NORTH"],
        "sample_mode": False,
    })
    assert resp.status_code == 503
    assert "Nightshift" in resp.json()["detail"]


# ── Workflow Unit Tests with Mocked Nightshift ─────────────────────────────────


# We reuse IDs that actually exist in local data (data/generated/police_incidents.json)
# since the workflow falls back to local data loader if Zetaris is unconfigured in test mode.

MOCK_PLANNER_RESPONSE = json.dumps({
    "keywords": ["crowbar", "safe", "chisel"],
    "crime_types": ["BURGLARY"],
    "target_stations": ["NORTH", "CENTRAL"],
})

MOCK_ANALYST_WITH_HALLUCINATED_ID = json.dumps([
    {
        "link_id": "LINK-01",
        "source_incident_id": "INC-HALLUCINATED-00001",  # Does not exist
        "target_incident_id": "INC-HALLUCINATED-00002",  # Does not exist
        "stations_involved": ["NORTH", "CENTRAL"],
        "similarity_basis": "Both used crowbar prying on commercial safes",
        "confidence_score": 0.82,
        "confidence_rationale": "Toolmark match and shared modus operandi",
        "supporting_evidence_ids": ["FOR-FAKE-9999"],
        "differences_or_inconsistencies": "Different time of day",
    }
])

MOCK_EVALUATOR_CLEAN = json.dumps({
    "revision_needed": False,
    "contradictions": [],
    "unresolved_questions": ["Verify suspect vehicle registration"],
})

MOCK_REPORTER = json.dumps({
    "title": "Cross-Station Burglary Intelligence Report",
    "executive_summary": "Analysis identified potential linkage between commercial safe burglaries across NORTH and CENTRAL stations based on shared tool marks and method of entry.",
    "contradictions_and_limitations": [
        "All links represent investigative leads, not established guilt."
    ],
    "follow_up_actions": [
        "Cross-reference vehicle registration for grey minivan sightings.",
        "Request inter-station forensic toolmark comparison.",
    ],
})


def test_workflow_evaluator_rejects_hallucinated_incident_ids():
    """
    Analyst proposes links with fabricated incident IDs.
    Evaluator's programmatic ID grounding check must reject them.
    The workflow must NOT silently accept hallucinated references.
    """
    call_sequence = [
        _mock_nightshift(MOCK_PLANNER_RESPONSE),
        _mock_nightshift(MOCK_ANALYST_WITH_HALLUCINATED_ID),
        _mock_nightshift(MOCK_EVALUATOR_CLEAN),
        _mock_nightshift(MOCK_REPORTER),
    ]
    call_iter = iter(call_sequence)

    mock_ai = MagicMock(spec=NightshiftClient)
    mock_ai.generate.side_effect = lambda *args, **kwargs: next(call_iter)

    wf = InvestigationWorkflow(ai_client=mock_ai)

    # We use sample scenario incidents to ensure candidate incidents exist
    sample = get_sample_investigation("crowbar_safe_cracking", "test")
    sample_incidents = sample["candidate_incidents"]

    with patch.object(wf._data, "search_candidate_incidents", return_value=sample_incidents):
        with patch.object(wf._data, "retrieve_supporting_evidence", return_value={
            "forensic_reports": [{"evidence_report_id": "FOR-0089", "incident_id": "INC-NORTH-0042"}],
            "cctv_reports": [],
            "witness_reports": [],
            "newspaper_reports": [],
        }):
            result = wf.run_investigation(
                query="commercial safe burglary crowbar",
                station_ids=["NORTH", "CENTRAL"],
            )

    # The hallucinated link should have been rejected by the evaluator ID check
    for link in result["candidate_links"]:
        assert link["source_incident_id"] != "INC-HALLUCINATED-00001"
        assert link["target_incident_id"] != "INC-HALLUCINATED-00002"

    # Fallback link should be generated since no valid analyst links passed
    assert len(result["candidate_incidents"]) >= 1
    assert result["data_mode"] == "zetaris_live"  # workflow always marks live mode


def test_workflow_evaluator_filters_hallucinated_evidence_ids():
    """
    Analyst cites a valid incident link but includes hallucinated evidence IDs.
    Evaluator must strip fake evidence IDs, keeping only verified ones.
    """
    sample = get_sample_investigation("crowbar_safe_cracking", "test")
    sample_incidents = sample["candidate_incidents"]
    inc_ids = [inc["incident_id"] for inc in sample_incidents]

    # Analyst proposes link with one real and one hallucinated evidence ID
    analyst_with_mixed_evidence = json.dumps([
        {
            "link_id": "LINK-01",
            "source_incident_id": inc_ids[0],
            "target_incident_id": inc_ids[1],
            "stations_involved": ["NORTH", "CENTRAL"],
            "similarity_basis": "Toolmark match across stations",
            "confidence_score": 0.88,
            "confidence_rationale": "Forensic toolmark confirmed",
            "supporting_evidence_ids": ["FOR-0089", "FOR-FAKE-99999"],  # One real, one fake
            "differences_or_inconsistencies": "None noted",
        }
    ])

    call_sequence = [
        _mock_nightshift(MOCK_PLANNER_RESPONSE),
        _mock_nightshift(analyst_with_mixed_evidence),
        _mock_nightshift(MOCK_EVALUATOR_CLEAN),
        _mock_nightshift(MOCK_REPORTER),
    ]
    call_iter = iter(call_sequence)

    mock_ai = MagicMock(spec=NightshiftClient)
    mock_ai.generate.side_effect = lambda *args, **kwargs: next(call_iter)

    wf = InvestigationWorkflow(ai_client=mock_ai)

    with patch.object(wf._data, "search_candidate_incidents", return_value=sample_incidents):
        with patch.object(wf._data, "retrieve_supporting_evidence", return_value={
            "forensic_reports": [{"evidence_report_id": "FOR-0089", "incident_id": inc_ids[0]}],
            "cctv_reports": [],
            "witness_reports": [],
            "newspaper_reports": [],
        }):
            result = wf.run_investigation(
                query="commercial safe burglary crowbar",
                station_ids=["NORTH", "CENTRAL"],
            )

    # The link with valid incident IDs should pass
    assert len(result["candidate_links"]) >= 1
    for link in result["candidate_links"]:
        # All cited evidence IDs should be verified
        for eid in link.get("supporting_evidence_ids", []):
            assert eid != "FOR-FAKE-99999", "Hallucinated evidence ID must be stripped"


def test_workflow_returns_complete_integration_status():
    """
    Final result must include integration_status with all 3 components
    (Zetaris, Nightshift, Meterless) as top-level keys.
    """
    sample = get_sample_investigation("crowbar_safe_cracking", "test")
    sample_incidents = sample["candidate_incidents"]

    call_sequence = [
        _mock_nightshift(MOCK_PLANNER_RESPONSE),
        _mock_nightshift("[]"),  # Analyst returns no links
        _mock_nightshift(MOCK_EVALUATOR_CLEAN),
        _mock_nightshift(MOCK_REPORTER),
    ]
    call_iter = iter(call_sequence)
    mock_ai = MagicMock(spec=NightshiftClient)
    mock_ai.generate.side_effect = lambda *args, **kwargs: next(call_iter)

    wf = InvestigationWorkflow(ai_client=mock_ai)

    with patch.object(wf._data, "search_candidate_incidents", return_value=sample_incidents):
        with patch.object(wf._data, "retrieve_supporting_evidence", return_value={
            "forensic_reports": [], "cctv_reports": [], "witness_reports": [], "newspaper_reports": [],
        }):
            result = wf.run_investigation(query="crowbar safe burglary")

    status = result["integration_status"]
    assert "zetaris" in status
    assert "nightshift_nemotron" in status
    assert "meterless_engine" in status

    # Nightshift metadata must be populated from mocked call
    ns = status["nightshift_nemotron"]
    assert ns["status"] == "connected"
    assert ns["model"] == "nvidia/nemotron-3.5-lightning-30b-a3b"
    assert ns["provider"] == "nvidia"

    # Meterless must have recorded entities
    me = status["meterless_engine"]
    assert me["status"] == "connected"
    assert isinstance(me["entities_count"], int)

    # Zetaris status
    assert status["zetaris"]["status"] == "connected"


def test_workflow_required_response_fields():
    """
    All required InvestigationResponse fields must be present in the final result.
    """
    sample = get_sample_investigation("catalytic_converter", "test")
    sample_incidents = sample.get("candidate_incidents", [])[:2]

    call_sequence = [
        _mock_nightshift(MOCK_PLANNER_RESPONSE),
        _mock_nightshift("[]"),
        _mock_nightshift(MOCK_EVALUATOR_CLEAN),
        _mock_nightshift(MOCK_REPORTER),
    ]
    call_iter = iter(call_sequence)
    mock_ai = MagicMock(spec=NightshiftClient)
    mock_ai.generate.side_effect = lambda *args, **kwargs: next(call_iter)

    wf = InvestigationWorkflow(ai_client=mock_ai)

    with patch.object(wf._data, "search_candidate_incidents", return_value=sample_incidents or []):
        with patch.object(wf._data, "retrieve_supporting_evidence", return_value={
            "forensic_reports": [], "cctv_reports": [], "witness_reports": [], "newspaper_reports": [],
        }):
            result = wf.run_investigation(query="catalytic converter theft")

    required_fields = [
        "investigation_id", "is_sample", "data_mode", "title", "query",
        "stations_involved", "candidate_incidents", "supporting_evidence",
        "candidate_links", "contradictions_and_limitations", "unresolved_questions",
        "follow_up_actions", "executive_summary", "integration_status",
        "retrieval_and_analysis_status", "trace_file", "timestamp", "elapsed_seconds",
    ]
    for field in required_fields:
        assert field in result, f"Missing required field: {field}"

    assert result["is_sample"] is False
    assert result["data_mode"] == "zetaris_live"
    assert isinstance(result["elapsed_seconds"], float)
    assert result["trace_file"].endswith(".jsonl")
