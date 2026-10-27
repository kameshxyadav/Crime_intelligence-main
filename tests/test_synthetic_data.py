"""
Automated Test Suite for Synthetic Crime Intelligence Data Generator
Open Agent Hackathon 2026
"""

import json
import os
import re
import sys
from datetime import datetime
import pytest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.generate_synthetic_data import generate_all
DATA_GEN_DIR = os.path.join(BASE_DIR, "data", "generated")
DATA_EVAL_DIR = os.path.join(BASE_DIR, "data", "evaluation")

EXPECTED_COUNTS = {
    "police_incidents.json": 3000,
    "newspaper_reports.json": 1500,
    "witness_reports.json": 2000,
    "cctv_reports.json": 2000,
    "forensic_reports.json": 1500,
}

EXPECTED_SCHEMAS = {
    "police_incidents.json": {
        "incident_id",
        "station_id",
        "reported_at",
        "occurred_from",
        "occurred_to",
        "crime_type",
        "location_id",
        "location_description",
        "method_description",
        "property_involved",
        "estimated_loss",
        "status",
        "source_reference_ids",
        "data_quality",
    },
    "newspaper_reports.json": {
        "news_id",
        "publication_name",
        "published_at",
        "headline",
        "article_text",
        "mentioned_date_from",
        "mentioned_date_to",
        "mentioned_location_ids",
        "crime_labels",
        "mentioned_property",
        "related_incident_ids",
        "source_reliability",
        "data_quality",
    },
    "witness_reports.json": {
        "witness_report_id",
        "submitted_at",
        "observed_from",
        "observed_to",
        "location_id",
        "observation_text",
        "observed_entities",
        "vehicle_description",
        "direction_of_travel",
        "confidence_level",
        "related_incident_ids",
        "contradiction_flags",
        "data_quality",
    },
    "cctv_reports.json": {
        "cctv_report_id",
        "camera_id",
        "location_id",
        "recorded_from",
        "recorded_to",
        "observed_entities",
        "vehicle_description",
        "vehicle_color",
        "partial_plate",
        "movement_description",
        "image_quality",
        "observation_confidence",
        "related_incident_ids",
        "data_quality",
    },
    "forensic_reports.json": {
        "evidence_report_id",
        "incident_id",
        "evidence_item_id",
        "collected_at",
        "location_id",
        "evidence_type",
        "description",
        "examination_method",
        "result_summary",
        "result_status",
        "confidence_level",
        "compared_evidence_ids",
        "limitations",
        "data_quality",
    },
}

TIMESTAMP_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


@pytest.fixture(scope="session")
def loaded_data():
    """Load all 5 datasets and ground truth once for test suite."""
    data = {}
    for filename in EXPECTED_COUNTS:
        filepath = os.path.join(DATA_GEN_DIR, filename)
        assert os.path.exists(filepath), f"Missing data file: {filepath}"
        with open(filepath, "r", encoding="utf-8") as f:
            data[filename] = json.load(f)

    gt_path = os.path.join(DATA_EVAL_DIR, "ground_truth.json")
    assert os.path.exists(gt_path), f"Missing ground truth file: {gt_path}"
    with open(gt_path, "r", encoding="utf-8") as f:
        data["ground_truth.json"] = json.load(f)

    return data


def test_individual_and_total_record_counts(loaded_data):
    """Checks that every file matches its exact quota and total is exactly 10,000."""
    total_records = 0
    for filename, expected_count in EXPECTED_COUNTS.items():
        actual_count = len(loaded_data[filename])
        assert actual_count == expected_count, (
            f"{filename} has {actual_count} records; expected exactly {expected_count}"
        )
        total_records += actual_count

    assert total_records == 10000, f"Expected total 10,000 records, got {total_records}"


def test_schema_field_names_exact_match(loaded_data):
    """Validates that every single record has the exact schema keys without missing or extra fields."""
    for filename, expected_fields in EXPECTED_SCHEMAS.items():
        records = loaded_data[filename]
        for idx, record in enumerate(records):
            record_keys = set(record.keys())
            missing = expected_fields - record_keys
            extra = record_keys - expected_fields
            assert not missing, f"{filename} record #{idx} missing keys: {missing}"
            assert not extra, f"{filename} record #{idx} unexpected extra keys: {extra}"


def test_timestamp_formats_iso8601_utc_z(loaded_data):
    """Validates that all timestamp strings are ISO 8601 ending in 'Z' or valid nulls."""
    mandatory_timestamps = {
        "police_incidents.json": ["reported_at", "occurred_from"],
        "newspaper_reports.json": ["published_at"],
        "witness_reports.json": ["submitted_at", "observed_from"],
        "cctv_reports.json": ["recorded_from"],
        "forensic_reports.json": ["collected_at"],
    }

    optional_timestamps = {
        "police_incidents.json": ["occurred_to"],
        "newspaper_reports.json": ["mentioned_date_from", "mentioned_date_to"],
        "witness_reports.json": ["observed_to"],
        "cctv_reports.json": ["recorded_to"],
        "forensic_reports.json": [],
    }

    for filename, fields in mandatory_timestamps.items():
        for idx, rec in enumerate(loaded_data[filename]):
            for field in fields:
                val = rec[field]
                assert isinstance(val, str), f"{filename} rec #{idx} mandatory timestamp {field} is not str: {val}"
                assert TIMESTAMP_REGEX.match(val), (
                    f"{filename} rec #{idx} timestamp {field} invalid ISO 8601 UTC format: {val}"
                )

    for filename, fields in optional_timestamps.items():
        for idx, rec in enumerate(loaded_data[filename]):
            for field in fields:
                val = rec[field]
                if val is not None:
                    assert isinstance(val, str), f"{filename} rec #{idx} optional timestamp {field} not str: {val}"
                    assert TIMESTAMP_REGEX.match(val), (
                        f"{filename} rec #{idx} optional timestamp {field} invalid format: {val}"
                    )


def test_station_ids_in_police_incidents(loaded_data):
    """Validates that station_id only contains NORTH, CENTRAL, or RIVERSIDE with good distribution."""
    stations = {"NORTH", "CENTRAL", "RIVERSIDE"}
    counts = {s: 0 for s in stations}
    for rec in loaded_data["police_incidents.json"]:
        sid = rec["station_id"]
        assert sid in stations, f"Invalid station_id: {sid}"
        counts[sid] += 1

    # Check balanced coverage across all 3 stations
    for s, cnt in counts.items():
        assert cnt >= 700, f"Station {s} has only {cnt} incidents, expected balanced distribution"


def test_list_and_scalar_data_types(loaded_data):
    """Ensures arrays are lists (empty or populated) and scalar nulls are handled correctly."""
    list_fields = {
        "police_incidents.json": ["property_involved", "source_reference_ids"],
        "newspaper_reports.json": ["mentioned_location_ids", "crime_labels", "mentioned_property", "related_incident_ids"],
        "witness_reports.json": ["observed_entities", "related_incident_ids", "contradiction_flags"],
        "cctv_reports.json": ["observed_entities", "related_incident_ids"],
        "forensic_reports.json": ["compared_evidence_ids"],
    }

    for filename, fields in list_fields.items():
        for idx, rec in enumerate(loaded_data[filename]):
            for field in fields:
                val = rec[field]
                assert isinstance(val, list), f"{filename} rec #{idx} field {field} must be list, got {type(val)}"

    # Specific scalar type checks
    for idx, rec in enumerate(loaded_data["police_incidents.json"]):
        loss = rec["estimated_loss"]
        assert loss is None or isinstance(loss, (float, int)), f"estimated_loss in rec #{idx} must be float/int/None"

    for idx, rec in enumerate(loaded_data["cctv_reports.json"]):
        conf = rec["observation_confidence"]
        assert isinstance(conf, (float, int)), f"cctv observation_confidence rec #{idx} must be numeric"
        assert 0.0 <= conf <= 1.0, f"cctv observation_confidence rec #{idx} out of range [0, 1]: {conf}"


def test_ground_truth_structure_and_referential_integrity(loaded_data):
    """Validates that ground truth file contains valid scenarios and all referenced IDs exist."""
    ground_truth = loaded_data["ground_truth.json"]
    assert isinstance(ground_truth, list), "ground_truth.json must be a list of scenarios"
    assert len(ground_truth) >= 6, "Expected at least 6 planted scenarios in ground truth"

    # Index all generated records
    incident_ids = {r["incident_id"] for r in loaded_data["police_incidents.json"]}
    witness_ids = {r["witness_report_id"] for r in loaded_data["witness_reports.json"]}
    cctv_ids = {r["cctv_report_id"] for r in loaded_data["cctv_reports.json"]}
    forensic_ids = {r["evidence_report_id"] for r in loaded_data["forensic_reports.json"]}
    news_ids = {r["news_id"] for r in loaded_data["newspaper_reports.json"]}

    required_gt_keys = {
        "relationship_id",
        "title",
        "stations_involved",
        "incident_ids",
        "source_record_ids",
        "why_related",
        "supporting_evidence",
        "contradictions_and_limitations",
        "confidence_label",
    }

    for scenario in ground_truth:
        missing_keys = required_gt_keys - set(scenario.keys())
        assert not missing_keys, f"Ground truth scenario {scenario.get('relationship_id')} missing keys: {missing_keys}"

        # Check incident IDs exist in police_incidents.json
        for inc_id in scenario["incident_ids"]:
            assert inc_id in incident_ids, f"Referenced incident {inc_id} not found in police_incidents.json"

        # Check source record IDs exist
        src = scenario["source_record_ids"]
        for wid in src.get("witness_reports", []):
            assert wid in witness_ids, f"Referenced witness {wid} not found in witness_reports.json"
        for cid in src.get("cctv_reports", []):
            assert cid in cctv_ids, f"Referenced cctv {cid} not found in cctv_reports.json"
        for fid in src.get("forensic_reports", []):
            assert fid in forensic_ids, f"Referenced forensic {fid} not found in forensic_reports.json"
        for nid in src.get("newspaper_reports", []):
            assert nid in news_ids, f"Referenced news {nid} not found in newspaper_reports.json"

        assert scenario["confidence_label"] in ["HIGH", "MEDIUM", "LOW", "EXCLUSION"]


def test_no_ground_truth_leakage_in_source_files(loaded_data):
    """Verifies that ground-truth labels are not leaked into the 5 source files."""
    forbidden_keys = {"relationship_id", "planted_reason", "ground_truth", "expected_conclusion"}
    for filename in EXPECTED_COUNTS:
        for idx, rec in enumerate(loaded_data[filename]):
            leaked = forbidden_keys.intersection(set(rec.keys()))
            assert not leaked, f"{filename} rec #{idx} contains ground truth leak keys: {leaked}"


def test_unique_primary_keys(loaded_data):
    """Ensures that every record in each dataset has a unique primary key identifier."""
    pk_mapping = {
        "police_incidents.json": "incident_id",
        "newspaper_reports.json": "news_id",
        "witness_reports.json": "witness_report_id",
        "cctv_reports.json": "cctv_report_id",
        "forensic_reports.json": "evidence_report_id",
    }
    for filename, pk in pk_mapping.items():
        records = loaded_data[filename]
        ids = [r[pk] for r in records]
        assert len(ids) == len(set(ids)), f"{filename} contains duplicate {pk} values!"


def test_date_range_bounds(loaded_data):
    """Ensures timestamps fall within the 2025-2026 synthetic timeline window."""
    for filename in EXPECTED_COUNTS:
        for idx, rec in enumerate(loaded_data[filename]):
            for k, v in rec.items():
                if isinstance(v, str) and TIMESTAMP_REGEX.match(v):
                    year = int(v[:4])
                    assert 2025 <= year <= 2026, (
                        f"{filename} rec #{idx} timestamp field '{k}' has unexpected year: {v}"
                    )


def test_utf8_encoding_and_json_array_format():
    """Verifies that all 5 files are strictly valid UTF-8 JSON arrays."""
    for filename in EXPECTED_COUNTS:
        filepath = os.path.join(DATA_GEN_DIR, filename)
        with open(filepath, "rb") as f:
            raw_bytes = f.read()
            # Must decode strictly as UTF-8 without errors
            text = raw_bytes.decode("utf-8")
            assert not text.startswith("\ufeff"), f"{filename} contains UTF-8 BOM"
            data = json.loads(text)
            assert isinstance(data, list), f"{filename} is not a JSON array"


def test_location_and_crime_type_diversity(loaded_data):
    """Verifies broad distribution of fictional locations and varied crime types."""
    locations = set()
    crime_types = set()
    for rec in loaded_data["police_incidents.json"]:
        locations.add(rec["location_id"])
        crime_types.add(rec["crime_type"])

    assert len(locations) >= 45, f"Expected at least 45 unique locations, got {len(locations)}"
    assert len(crime_types) >= 8, f"Expected at least 8 crime types, got {len(crime_types)}"


def test_cross_station_planted_scenarios(loaded_data):
    """Verifies that planted scenarios include multi-station relationships."""
    ground_truth = loaded_data["ground_truth.json"]
    multi_station_scenarios = [
        s for s in ground_truth if len(s.get("stations_involved", [])) > 1
    ]
    assert len(multi_station_scenarios) >= 4, (
        f"Expected at least 4 multi-station scenarios, found {len(multi_station_scenarios)}"
    )


def test_generator_reproducibility(tmp_path):
    """Ensures rerunning generator with seed 42 produces identical output."""
    res1 = generate_all(seed=42)
    res2 = generate_all(seed=42)
    assert res1["total_records"] == res2["total_records"]
    assert res1["record_counts"] == res2["record_counts"]

