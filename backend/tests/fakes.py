"""Test doubles for the multi-agent workflow (clearly mocked: no network, no Zetaris)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.services.model_registry import CallRecord
from app.services.nightshift_client import NightshiftResponse

INC_A = {"incident_id": "INC-NORTH-0001", "station_id": "NORTH", "crime_type": "BURGLARY", "location_id": "LOC-NORTH-01",
         "occurred_from": "2025-03-01T01:00:00Z", "occurred_to": "2025-03-01T02:00:00Z", "reported_at": "2025-03-01T08:00:00Z",
         "method_description": "Pried rear door with 36mm chisel-tip pry bar", "property_involved": ["safe"], "status": "OPEN",
         "data_quality": "HIGH"}
INC_B = {"incident_id": "INC-CEN-0002", "station_id": "CENTRAL", "crime_type": "BURGLARY", "location_id": "LOC-CEN-02",
         "occurred_from": "2025-03-05T01:00:00Z", "occurred_to": "2025-03-05T03:00:00Z", "reported_at": "2025-03-05T09:00:00Z",
         "method_description": "Forced office door using chisel-tip pry bar", "property_involved": ["safe"], "status": "OPEN",
         "data_quality": "HIGH"}
INC_C = {"incident_id": "INC-RIV-0003", "station_id": "RIVERSIDE", "crime_type": "BURGLARY", "location_id": "LOC-RIV-03",
         "occurred_from": "2025-03-07T01:00:00Z", "occurred_to": "2025-03-07T02:00:00Z", "reported_at": "2025-03-07T09:00:00Z",
         "method_description": "Pry bar used on warehouse door", "property_involved": ["tools"], "status": "OPEN", "data_quality": "MEDIUM"}

FOR_A = {"evidence_report_id": "FOR-0001", "evidence_item_id": "EVD-0001", "incident_id": "INC-NORTH-0001", "location_id": "LOC-NORTH-01",
         "evidence_type": "TOOLMARK", "description": "Chisel-tip toolmark striations 36mm", "result_status": "MATCH_CONFIRMED"}
FOR_B = {"evidence_report_id": "FOR-0002", "evidence_item_id": "EVD-0002", "incident_id": "INC-CEN-0002", "location_id": "LOC-CEN-02",
         "evidence_type": "TOOLMARK", "description": "Chisel-tip toolmark striations 36mm", "result_status": "MATCH_CONFIRMED"}
CCTV_A = {"cctv_report_id": "CCTV-0001", "camera_id": "CAM-1", "location_id": "LOC-NORTH-01", "recorded_from": "2025-03-01T00:50:00Z",
          "recorded_to": "2025-03-01T01:40:00Z", "vehicle_description": "grey minivan", "vehicle_color": "grey",
          "related_incident_ids": ["INC-NORTH-0001"]}
CCTV_A_DUP = {**CCTV_A, "cctv_report_id": "CCTV-0009", "recorded_from": "2025-03-01T01:10:00Z", "recorded_to": "2025-03-01T02:00:00Z"}
WIT_B = {"witness_report_id": "WIT-0001", "location_id": "LOC-CEN-02", "observed_from": "2025-03-05T01:30:00Z",
         "observation_text": "Saw a grey minivan parked near the office", "vehicle_description": "grey minivan",
         "related_incident_ids": ["INC-CEN-0002"], "contradiction_flags": []}
WIT_B_RED = {**WIT_B, "witness_report_id": "WIT-0002", "observed_from": "2025-03-05T01:45:00Z",
             "observation_text": "A red sedan idled outside", "vehicle_description": "red sedan"}
NEWS_A = {"news_id": "NEWS-0001", "headline": "Burglary in North", "article_text": "Safe stolen after rear door pried.",
          "related_incident_ids": ["INC-NORTH-0001"]}

EMPTY_EV = {"cctv_reports": [], "witness_reports": [], "forensic_reports": [], "newspaper_reports": []}


def good_link(**over: Any) -> Dict[str, Any]:
    link = {
        "link_id": "LINK-01", "source_incident_id": "INC-NORTH-0001", "target_incident_id": "INC-CEN-0002",
        "stations_involved": ["NORTH", "CENTRAL"], "similarity_basis": "Same tool signature",
        "shared_attributes": [{"attribute": "tool", "value": "chisel-tip", "match_type": "exact", "source_ids": ["FOR-0001", "FOR-0002"]}],
        "differences": ["Different building types"], "missing_evidence": [],
        "supporting_evidence_ids": ["FOR-0001", "FOR-0002"], "quotes": [], "heuristic_score": 0.7, "score_note": "uncalibrated",
    }
    link.update(over)
    return link


class FakeData:
    """In-memory stand-in for ZetarisInvestigationService."""

    def __init__(self, incidents: List[Dict[str, Any]], evidence: Optional[Dict[str, List[Dict[str, Any]]]] = None,
                 fail_after_queries: Optional[int] = None) -> None:
        self.incidents = {i["incident_id"]: i for i in incidents}
        self.evidence = evidence or EMPTY_EV
        self.query_count = 0
        self.errors: List[str] = []
        self.calls: List[str] = []
        self.fail_after_queries = fail_after_queries

    def _tick(self, name: str) -> None:
        self.calls.append(name)
        self.query_count += 1
        if self.fail_after_queries is not None and self.query_count > self.fail_after_queries:
            from app.services.zetaris_adapter import ZetarisConnectionError
            raise ZetarisConnectionError("simulated Zetaris outage")

    def search_candidate_incidents(self, keywords=None, crime_types=None, station_ids=None, date_from=None, date_to=None, limit=15):
        self._tick("search")
        return [i for i in self.incidents.values() if not station_ids or i["station_id"] in station_ids][:limit]

    def get_incidents_by_ids(self, ids):
        self._tick("by_ids")
        return [self.incidents[i] for i in ids if i in self.incidents]

    def get_incidents_by_locations(self, locs, limit=10):
        self._tick("by_locations")
        return [i for i in self.incidents.values() if i["location_id"] in locs][:limit]

    def retrieve_supporting_evidence(self, incident_ids, location_ids, limit_per_source=10):
        self._tick("evidence")
        out = {k: [] for k in EMPTY_EV}
        for k, rows in self.evidence.items():
            for r in rows:
                rel = set(r.get("related_incident_ids") or []) | ({r["incident_id"]} if r.get("incident_id") else set())
                if rel & set(incident_ids) or r.get("location_id") in location_ids:
                    out[k].append(r)
        return out


class FakeRegistry:
    """Scripted registry: per-role queues of JSON strings (or Exceptions)."""

    def __init__(self, script: Dict[str, List[Any]], reported: Optional[Dict[str, str]] = None) -> None:
        self.script = {k: list(v) for k, v in script.items()}
        self.reported = reported or {}
        self.calls: List[tuple] = []

    def generate(self, role, messages, max_tokens=1200, temperature=0.2, timeout_seconds=None):
        self.calls.append((role, messages))
        queue = self.script.get(role, [])
        if not queue:
            raise AssertionError(f"unscripted model call for role {role}")
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        content = item if isinstance(item, str) else json.dumps(item)
        model = self.reported.get(role, "nvidia/nemotron-3.5-lightning-30b-a3b")
        resp = NightshiftResponse(content=content, model=model, provider="nvidia", receipt_id=f"rcpt_{len(self.calls)}",
                                  latency_ms=5.0, usage={"prompt_tokens": 100, "completion_tokens": 50})
        rec = CallRecord(role=role, requested_model=model, reported_model=model, provider="nvidia", receipt_id=resp.receipt_id,
                         latency_ms=5.0, routed_as_requested=True, prompt_tokens=100, completion_tokens=50)
        return resp, rec

    def report(self, probe: bool = False):
        return {"roles": {}, "fake": True}


PLAN_KEYWORDS = {"action": "retrieve", "rationale": "search tool marks",
                 "retrieval_requests": [{"kind": "keyword_search", "keywords": ["chisel"], "station_ids": ["NORTH", "CENTRAL"], "reason": "tool"}],
                 "outstanding_questions": []}
SKEPTIC_OK = {"review_status": "accepted_with_objections", "alternative_explanations": ["common tool"],
              "objections": [{"link_id": "LINK-01", "kind": "alternative_explanation", "description": "Chisel-tip bars are commonly sold.",
                              "cited_ids": ["FOR-0001"], "severity": "low"}]}
REPORT_OK = {"title": "Report", "executive_summary": "Possible tool-signature link.",
             "facts": [{"statement": "Toolmarks recorded at both scenes", "source_ids": ["FOR-0001", "FOR-0002"]}],
             "hypotheses": [{"statement": "Possible common tool use", "link_id": "LINK-01"}],
             "contradictions_and_limitations": [], "unresolved_questions": [], "follow_up_actions": ["Compare toolmarks"]}
