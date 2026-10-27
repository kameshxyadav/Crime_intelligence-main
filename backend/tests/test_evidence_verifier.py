"""Deterministic evidence verifier - pure unit tests (no network, no models)."""

from __future__ import annotations

from app.services.evidence_verifier import EvidenceIndex, cluster_independent, source_type_of, verify_cited_ids, verify_link
from tests.fakes import (CCTV_A, CCTV_A_DUP, FOR_A, FOR_B, INC_A, INC_B, INC_C, NEWS_A, WIT_B, WIT_B_RED, good_link)


def _index(incs=(INC_A, INC_B), **ev) -> EvidenceIndex:
    idx = EvidenceIndex()
    idx.add_incidents(incs)
    idx.add_evidence({"forensic_reports": ev.get("forensic", [FOR_A, FOR_B]), "cctv_reports": ev.get("cctv", []),
                      "witness_reports": ev.get("witness", []), "newspaper_reports": ev.get("news", [])})
    return idx


def _check(v, name):
    return next(c for c in v.checks if c.check == name)


def test_supported_when_two_independent_sources_and_all_checks_pass():
    v = verify_link(good_link(), _index())
    assert v.status == "SUPPORTED" and v.independent_source_count == 2
    assert _check(v, "ids_exist").status == "pass" and _check(v, "attributes").status == "pass"


def test_unknown_incident_id_is_unsupported():
    v = verify_link(good_link(target_incident_id="INC-HALLUCINATED-0009"), _index())
    assert v.status == "UNSUPPORTED" and "INC-HALLUCINATED-0009" in v.rejected_ids


def test_unknown_evidence_id_is_dropped_not_trusted():
    v = verify_link(good_link(supporting_evidence_ids=["FOR-0001", "FOR-9999"]), _index())
    assert "FOR-9999" in v.rejected_ids and "FOR-9999" not in v.verified_evidence_ids
    assert v.status == "WEAK" and v.independent_source_count == 1


def test_prefix_must_match_source_type():
    idx = _index()
    assert source_type_of("FOR-0001") == "forensic" and source_type_of("XYZ-1") is None
    assert verify_cited_ids(["FOR-0001", "FOR-9999"], idx) == {"valid": ["FOR-0001"], "invalid": ["FOR-9999"]}


def test_evidence_unrelated_to_the_incidents_is_not_counted():
    unrelated = {**FOR_A, "evidence_report_id": "FOR-7777", "evidence_item_id": "EVD-7777", "incident_id": "INC-OTHER-1", "location_id": "LOC-ELSEWHERE"}
    v = verify_link(good_link(supporting_evidence_ids=["FOR-7777"]), _index(forensic=[FOR_A, FOR_B, unrelated]))
    assert "FOR-7777" not in v.verified_evidence_ids and v.independent_source_count == 0


def test_duplicate_cctv_reports_count_once():
    idx = _index(cctv=[CCTV_A, CCTV_A_DUP], forensic=[])
    v = verify_link(good_link(supporting_evidence_ids=["CCTV-0001", "CCTV-0009"], shared_attributes=[]), idx)
    assert v.independent_source_count == 1 and v.duplicate_groups == [["CCTV-0001", "CCTV-0009"]]


def test_newspaper_about_a_police_incident_is_not_independent():
    idx = _index(news=[NEWS_A], forensic=[FOR_A, FOR_B])
    v = verify_link(good_link(supporting_evidence_ids=["NEWS-0001", "FOR-0001"], shared_attributes=[]), idx)
    assert v.independent_source_count == 1          # only the forensic report counts
    clusters, _ = cluster_independent(["NEWS-0001"], idx, ["INC-NORTH-0001", "INC-CEN-0002"])
    assert list(clusters) == ["police:INC-NORTH-0001"]


def test_forensic_exclusion_and_inconclusive_do_not_corroborate_and_exclusion_is_a_contradiction():
    excl = {**FOR_B, "result_status": "EXCLUSION"}
    v = verify_link(good_link(), _index(forensic=[FOR_A, excl]))
    assert v.independent_source_count == 1
    assert any(c["type"] == "forensic_exclusion" for c in v.contradictions)
    inc = {**FOR_B, "result_status": "INCONCLUSIVE"}
    assert verify_link(good_link(), _index(forensic=[FOR_A, inc])).independent_source_count == 1


def test_claimed_attribute_absent_from_cited_records_fails():
    attrs = [{"attribute": "plate", "value": "7XK***", "match_type": "exact", "source_ids": ["FOR-0001"]}]
    v = verify_link(good_link(shared_attributes=attrs), _index())
    assert v.status == "UNSUPPORTED" and _check(v, "attributes").status == "fail"


def test_attribute_evidenced_for_one_incident_only_is_not_shown_shared():
    attrs = [{"attribute": "tool", "value": "36mm", "match_type": "exact", "source_ids": ["FOR-0001"]}]
    v = verify_link(good_link(shared_attributes=attrs, supporting_evidence_ids=["FOR-0001"]), _index(incs=(INC_A, INC_B)))
    assert _check(v, "attributes").status == "warn"


def test_quotation_must_match_source_text():
    ok = verify_link(good_link(quotes=[{"source_id": "FOR-0001", "text": "chisel-tip  toolmark"}]), _index())
    assert _check(ok, "quotes").status == "pass"
    bad = verify_link(good_link(quotes=[{"source_id": "FOR-0001", "text": "the offender wore a red coat"}]), _index())
    assert bad.status == "UNSUPPORTED" and _check(bad, "quotes").status == "fail"


def test_station_mismatch_fails():
    v = verify_link(good_link(stations_involved=["NORTH", "RIVERSIDE"]), _index())
    assert _check(v, "station_consistency").status == "fail" and v.status == "UNSUPPORTED"


def test_overlapping_windows_at_different_stations_are_a_visible_contradiction():
    overlap = {**INC_B, "occurred_from": "2025-03-01T01:30:00Z", "occurred_to": "2025-03-01T02:30:00Z"}
    v = verify_link(good_link(), _index(incs=(INC_A, overlap)))
    assert _check(v, "timeline").status == "warn"
    assert any(c["type"] == "incompatible_timeline" for c in v.contradictions)


def test_missing_time_is_indeterminate_not_compatible():
    no_time = {**INC_B, "occurred_from": None, "occurred_to": None}
    v = verify_link(good_link(), _index(incs=(INC_A, no_time)))
    assert _check(v, "timeline").status == "indeterminate"


def test_vehicle_color_conflict_between_cctv_and_witness_is_kept():
    idx = _index(cctv=[CCTV_A], witness=[WIT_B_RED], forensic=[FOR_A, FOR_B])
    v = verify_link(good_link(supporting_evidence_ids=["CCTV-0001", "WIT-0002", "FOR-0001"], shared_attributes=[]), idx)
    assert any(c["type"] == "vehicle_color_conflict" for c in v.contradictions)
    ok = verify_link(good_link(supporting_evidence_ids=["CCTV-0001", "WIT-0001"], shared_attributes=[]), _index(cctv=[CCTV_A], witness=[WIT_B]))
    assert not any(c["type"] == "vehicle_color_conflict" for c in ok.contradictions)


def test_witness_source_flags_surface_as_contradictions():
    flagged = {**WIT_B, "contradiction_flags": ["divergent_vehicle_description"]}
    v = verify_link(good_link(supporting_evidence_ids=["WIT-0001"], shared_attributes=[]), _index(witness=[flagged], forensic=[]))
    assert any(c["flag"] == "divergent_vehicle_description" for c in v.contradictions)


def test_link_needs_two_distinct_incidents():
    assert verify_link(good_link(target_incident_id="INC-NORTH-0001"), _index()).status == "UNSUPPORTED"


def test_location_only_records_are_context_not_corroboration():
    near = {**FOR_A, "evidence_report_id": "FOR-5555", "evidence_item_id": "EVD-5555", "incident_id": None, "location_id": "LOC-NORTH-01"}
    v = verify_link(good_link(supporting_evidence_ids=["FOR-5555", "FOR-0002"]), _index(forensic=[FOR_A, FOR_B, near]))
    assert "FOR-5555" in v.contextual_ids and "FOR-5555" not in v.verified_evidence_ids
    assert v.independent_source_count == 1 and v.status == "WEAK"
