"""
Backend test suite for Cross-Station Crime Intelligence API.
Covers all endpoints, query parameters, error cases, and isolation checks.
"""

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.config import settings

client = TestClient(app)


# ── Health Endpoints ──────────────────────────────────────────────────────────


def test_app_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "environment" in data


def test_zetaris_health_unconfigured(monkeypatch):
    """When ZETARIS_ENABLED is forced off, the health endpoint must report not_configured."""
    monkeypatch.setattr(settings, "zetaris_enabled", False)
    response = client.get("/api/health/zetaris")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["mode"] == "local_fallback"
    assert data["configured"] is False
    assert "NOT CONFIGURED" in data["message"]


def test_zetaris_health_configured_flag(monkeypatch):
    """When ZETARIS_ENABLED is true the health endpoint must report configured=True."""
    # Patch the computed property directly since zetaris_configured requires credentials+enabled
    monkeypatch.setattr(
        type(settings), "zetaris_configured", property(lambda self: True)
    )
    # We only check that the key is present and True; a live connection is not required
    response = client.get("/api/health/zetaris")
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is True


# ── Dashboard Summary ─────────────────────────────────────────────────────────


def test_dashboard_summary():
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()

    assert data["total_incidents"] == 3000
    assert len(data["by_station"]) == 3
    station_names = {s["station_id"] for s in data["by_station"]}
    assert station_names == {"NORTH", "CENTRAL", "RIVERSIDE"}

    # Crime types: local loader returns exactly 10; Zetaris may return up to 20
    assert len(data["by_crime_type"]) >= 10
    assert len(data["by_status"]) == 4

    sources = {s["source"]: s["count"] for s in data["by_source"]}
    assert sources["police_incidents"] == 3000
    assert sources["newspaper_reports"] == 1500
    assert sources["witness_reports"] >= 2000
    assert sources["cctv_reports"] == 2000
    assert sources["forensic_reports"] == 1500

    assert len(data["incident_timeline"]) > 0
    # Accept either live Zetaris or local fallback
    assert data["data_mode"] in {"zetaris_live", "local_fallback"}


# ── Incidents Endpoints ───────────────────────────────────────────────────────


def test_list_incidents_default():
    response = client.get("/api/incidents")
    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["total"] == 3000
    assert len(data["items"]) == 50
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["total_pages"] == 60


def test_list_incidents_filtered_by_station():
    response = client.get("/api/incidents?station=NORTH&page_size=20")
    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["total"] == 971
    assert len(data["items"]) == 20
    assert all(item["station_id"] == "NORTH" for item in data["items"])


def test_list_incidents_filtered_by_crime_type():
    response = client.get("/api/incidents?crime_type=BURGLARY&page_size=20")
    assert response.status_code == 200
    data = response.json()
    assert all(item["crime_type"] == "BURGLARY" for item in data["items"])


def test_list_incidents_search():
    response = client.get("/api/incidents?search=theft&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["total"] > 0
    assert len(data["items"]) <= 10


def test_get_incident_by_id_success():
    # Fetch first incident to get a real ID
    list_resp = client.get("/api/incidents?page_size=1")
    assert list_resp.status_code == 200
    real_id = list_resp.json()["items"][0]["incident_id"]

    response = client.get(f"/api/incidents/{real_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == real_id
    assert "station_id" in data
    assert "crime_type" in data
    assert "method_description" in data


def test_get_incident_by_id_not_found():
    response = client.get("/api/incidents/INC-NONEXISTENT-999999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ── Sources Endpoints ─────────────────────────────────────────────────────────


def test_list_sources():
    response = client.get("/api/sources")
    assert response.status_code == 200
    data = response.json()
    source_names = {s["name"] for s in data["sources"]}
    assert source_names == {
        "police_incidents",
        "newspaper_reports",
        "witness_reports",
        "cctv_reports",
        "forensic_reports",
    }


def test_list_source_records():
    for src in ["police_incidents", "newspaper_reports", "witness_reports", "cctv_reports", "forensic_reports"]:
        response = client.get(f"/api/sources/{src}/records?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == src
        assert len(data["items"]) == 5
        assert data["pagination"]["total"] > 0


def test_list_source_records_invalid_source():
    response = client.get("/api/sources/unknown_source/records")
    assert response.status_code == 404


def test_get_source_record_by_id():
    # Fetch first record to get a valid ID
    list_resp = client.get("/api/sources/cctv_reports/records?page_size=1")
    assert list_resp.status_code == 200
    real_id = list_resp.json()["items"][0]["cctv_report_id"]

    response = client.get(f"/api/sources/cctv_reports/records/{real_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "cctv_reports"
    assert data["record"]["cctv_report_id"] == real_id


def test_get_source_record_by_id_not_found():
    response = client.get("/api/sources/cctv_reports/records/CCTV-999999")
    assert response.status_code == 404


# ── Evidence Linkage ──────────────────────────────────────────────────────────


def test_incident_evidence():
    # Get a real incident ID
    list_resp = client.get("/api/incidents?page_size=1")
    assert list_resp.status_code == 200
    real_id = list_resp.json()["items"][0]["incident_id"]

    response = client.get(f"/api/incidents/{real_id}/evidence")
    assert response.status_code == 200
    data = response.json()
    assert data["incident"]["incident_id"] == real_id
    assert "direct_links" in data
    assert "inferred_links" in data
    assert "data_mode" in data
    for item in data["direct_links"]:
        assert item["link_type"] == "direct_reference"
    for item in data["inferred_links"]:
        assert "inferred" in item["link_type"]


# ── Ground Truth Isolation Check ──────────────────────────────────────────────


def test_ground_truth_never_leaked():
    import sys
    for mod_name in sys.modules:
        assert "ground_truth" not in mod_name, f"ground_truth was imported as module: {mod_name}"


# ── Citizen Tip & Officer Review Tests ─────────────────────────────────────────


def test_submit_and_review_citizen_tip():
    # 1. Submit citizen tip
    submit_payload = {
        "station_id": "PS-SEC17",
        "crime_type": "BURGLARY",
        "observation_text": "Observed suspicious grey minivan parked near jewellery store at 03:00 AM.",
        "vehicle_description": "Grey Dodge Caravan 7XK***",
        "has_cctv_still": True,
        "confidence_level": "HIGH",
    }
    resp = client.post("/api/tips/submit", json=submit_payload)
    assert resp.status_code == 200
    tip_data = resp.json()
    assert "tip_id" in tip_data
    assert tip_data["guard_verdict"] == "CLEAN_EVIDENCE_LEAD"
    tip_id = tip_data["tip_id"]

    # 2. Get single tip
    get_resp = client.get(f"/api/tips/{tip_id}")
    assert get_resp.status_code == 200
    single_tip = get_resp.json()
    assert single_tip["tip_id"] == tip_id
    assert single_tip["review_status"] == "PENDING_REVIEW"

    # 3. Officer Review Action: Approve
    action_payload = {
        "review_status": "APPROVED",
        "officer_notes": "Toolmark striations matched 36mm safe pry marks in Sector 17 case.",
        "reviewed_by": "Insp. Rajesh Sharma (CHD-POL-1704)",
        "linked_incident_id": "INC-SEC17-0118",
    }
    action_resp = client.post(f"/api/tips/{tip_id}/action", json=action_payload)
    assert action_resp.status_code == 200
    updated_tip = action_resp.json()
    assert updated_tip["review_status"] == "APPROVED"
    assert updated_tip["reviewed_by"] == "Insp. Rajesh Sharma (CHD-POL-1704)"
    assert updated_tip["linked_incident_id"] == "INC-SEC17-0118"
    assert "Toolmark striations" in updated_tip["officer_notes"]

