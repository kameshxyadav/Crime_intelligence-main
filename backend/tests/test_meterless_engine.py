"""
Meterless World Model Engine Tests
==================================
Tests the real Meterless Engine capability (World Model) powering shared state
between agents. Verifies entity upsert, observation appending, contradiction
preservation, and agent provenance.
"""

import time
import pytest

from app.services.meterless_service import MeterlessWorldModelService


@pytest.fixture
def service(tmp_path):
    # Use temporary directory for isolated test persistence
    srv = MeterlessWorldModelService()
    srv._cfg.meterless_world_dir = str(tmp_path)
    return srv


def test_real_meterless_engine_world_operations(service):
    """
    Real Meterless Engine test exercising actual World Model operations
    through Node runner backed by worldmodel.js.
    """
    run_id = f"test_run_{int(time.time())}"

    # 1. Initialize World Model shared state
    init_res = service.init_investigation_state(
        run_id=run_id,
        query="Investigate safe burglary in North",
        target_stations=["NORTH", "CENTRAL"],
    )
    assert init_res["ok"] is True
    assert init_res["worldName"] == f"inv_{run_id}"

    # 2. Upsert Candidate Incident Entity
    candidates = service.record_candidate_incidents(
        run_id=run_id,
        incidents=[
            {
                "incident_id": "INC-NORTH-0042",
                "station_id": "NORTH",
                "crime_type": "BURGLARY",
                "location_id": "LOC-NORTH-01",
                "method_description": "Safe door peeled using 36mm chisel pry tool",
            }
        ],
    )
    assert len(candidates) == 1
    assert candidates[0]["ok"] is True
    entity = candidates[0]["entity"]
    assert entity["name"] == "INC-NORTH-0042"
    assert entity["schemaVersion"] == 1
    assert "ent_" in entity["id"]

    # 3. Analyst contributes finding observation
    finding_res = service.record_analyst_finding(
        run_id=run_id,
        finding_id="f1",
        entity_ids=[entity["id"]],
        claim="Toolmark striations match 36mm chisel",
        evidence_ids=["FOR-0089"],
        stations_involved=["NORTH", "CENTRAL"],
        similarity_basis="Toolmark comparison",
    )
    assert finding_res["ok"] is True

    # 4. Evaluator adds contradiction observation
    eval_res = service.record_evaluator_feedback(
        run_id=run_id,
        feedback_id="e1",
        entity_ids=[entity["id"]],
        evaluation_verdict="CONTRADICTED",
        claim="Witness reported red sedan, conflicting with CCTV minivan",
        contradiction_flags=["vehicle_discrepancy"],
        unresolved_questions=["Verify registration 7XK***"],
        revision_requested=False,
    )
    assert eval_res["ok"] is True

    # 5. Retrieve complete investigation state & verify contradiction preserved
    state = service.get_investigation_state(run_id)
    assert state["entities_count"] == 2  # 1 investigation + 1 incident
    assert state["observations_count"] == 2  # 1 analyst finding + 1 evaluator feedback
    assert len(state["contradictions"]) == 1
    assert state["contradictions"][0]["payload"]["claim"] == "Witness reported red sedan, conflicting with CCTV minivan"
    assert "vehicle_discrepancy" in state["contradictions"][0]["payload"]["contradiction_flags"]


def test_meterless_contradiction_preservation(service):
    """
    Verifies that multiple conflicting claims are preserved rather than silently overwritten.
    """
    run_id = f"test_contra_{int(time.time())}"
    service.init_investigation_state(run_id, "Test contradictions", ["NORTH"])

    # First contradiction: vehicle discrepancy
    service.record_evaluator_feedback(
        run_id=run_id,
        feedback_id="contra_1",
        entity_ids=["INC-NORTH-0042"],
        evaluation_verdict="CONTRADICTED",
        claim="Eyewitness reports sedan, while CCTV reports minivan",
        contradiction_flags=["vehicle_discrepancy"],
        unresolved_questions=[],
    )

    # Second contradiction: suspect count discrepancy
    service.record_evaluator_feedback(
        run_id=run_id,
        feedback_id="contra_2",
        entity_ids=["INC-NORTH-0042"],
        evaluation_verdict="CONTRADICTED",
        claim="Witness A states lone suspect, witness B saw three individuals",
        contradiction_flags=["suspect_count_discrepancy"],
        unresolved_questions=[],
    )

    state = service.get_investigation_state(run_id)
    # Both contradictions must be preserved!
    assert len(state["contradictions"]) == 2
    claims = [c["payload"]["claim"] for c in state["contradictions"]]
    assert any("sedan" in c for c in claims)
    assert any("lone suspect" in c for c in claims)


def test_meterless_agent_provenance(service):
    """
    Verifies that agent identities are recorded and retrievable.
    """
    run_id = f"test_prov_{int(time.time())}"
    service.init_investigation_state(run_id, "Test provenance", ["NORTH"])

    service.record_analyst_finding(
        run_id=run_id,
        finding_id="f1",
        entity_ids=["INC-NORTH-0042"],
        claim="Fingerprint latent scan on safe dial",
        evidence_ids=["FOR-0010"],
        stations_involved=["NORTH"],
        similarity_basis="Latent scan",
    )

    service.record_reporter_synthesis(
        run_id=run_id,
        synthesis_id="s1",
        summary="Final investigative synthesis",
        candidate_links_count=1,
        contradictions_count=0,
        recommended_actions=["Interview witness"],
    )

    state = service.get_investigation_state(run_id)
    assert len(state["analyst_findings"]) == 1
    assert state["analyst_findings"][0]["payload"]["agent"] == "analyst"

    assert len(state["reporter_syntheses"]) == 1
    assert state["reporter_syntheses"][0]["payload"]["agent"] == "reporter"


def test_meterless_health_check(service):
    """Verifies that health_check reports connected engine status."""
    health = service.health_check()
    assert health["status"] == "connected"
    assert health["engine"] == "meterless_world_model"
    assert health["schema_version"] == 1
    assert health["configured"] is True
