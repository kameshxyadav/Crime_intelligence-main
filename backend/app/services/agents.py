"""
Investigation Agents
====================
Four agents with distinct roles, prompts, structured outputs and checks:

  Planner   plans retrieval, decides to continue / conclude / stop (no data access)
  Finder    analyses records retrieved from Zetaris and proposes cross-station links
  Skeptic   independently attacks the links; may demand more retrieval
  Reporter  writes the report from validated state only

Each agent call goes through the ModelRegistry (so Nightshift is the only
route and the model that actually answered is recorded). Outputs are parsed
into pydantic contracts; one repair attempt is made on malformed output, then
``AgentOutputError`` is raised - there is no silent default.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Type, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.services.model_registry import CallRecord, ModelRegistry

T = TypeVar("T", bound=BaseModel)


class AgentOutputError(Exception):
    """Model output could not be parsed into the agent's contract."""

    def __init__(self, role: str, message: str, calls: List[CallRecord]):
        super().__init__(f"{role}: {message}")
        self.role, self.calls = role, calls


def extract_json_block(text: str) -> Optional[Any]:
    """Extract and parse a JSON object or array from model text."""
    if not text:
        return None
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    candidate = match.group(1).strip() if match else text.strip()
    try:
        return json.loads(candidate)
    except Exception:
        obj = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", candidate)
        if obj:
            try:
                return json.loads(obj.group(1))
            except Exception:
                return None
    return None


# ── contracts ────────────────────────────────────────────────────────────────
class _Lenient(BaseModel):
    model_config = ConfigDict(extra="ignore")


class RetrievalRequest(_Lenient):
    kind: Literal["keyword_search", "by_incident_ids", "related_records", "location_window"]
    keywords: List[str] = Field(default_factory=list)
    crime_types: List[str] = Field(default_factory=list)
    station_ids: List[str] = Field(default_factory=list)
    incident_ids: List[str] = Field(default_factory=list)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    reason: str = ""


class PlannerDecision(_Lenient):
    action: Literal["retrieve", "conclude", "blocked"]
    rationale: str = ""
    evidence_needed: List[str] = Field(default_factory=list)
    retrieval_requests: List[RetrievalRequest] = Field(default_factory=list)
    outstanding_questions: List[str] = Field(default_factory=list)


class SharedAttribute(_Lenient):
    attribute: str
    value: str
    match_type: Literal["exact", "semantic"] = "semantic"
    source_ids: List[str] = Field(default_factory=list)


class Quote(_Lenient):
    source_id: str
    text: str


class FinderLink(_Lenient):
    link_id: str
    source_incident_id: str
    target_incident_id: str
    stations_involved: List[str] = Field(default_factory=list)
    similarity_basis: str = ""
    shared_attributes: List[SharedAttribute] = Field(default_factory=list)
    differences: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    quotes: List[Quote] = Field(default_factory=list)
    heuristic_score: float = Field(default=0.0, ge=0.0, le=1.0)
    score_note: str = ""


class FinderOutput(_Lenient):
    links: List[FinderLink] = Field(default_factory=list)
    withdrawn_link_ids: List[str] = Field(default_factory=list)
    notes: str = ""


ObjectionKind = Literal["contradiction", "timeline", "unsupported_claim", "circular_reasoning",
                        "alternative_explanation", "missing_evidence", "duplicate_source", "other"]


_OBJECTION_KINDS = ("contradiction", "timeline", "unsupported_claim", "circular_reasoning",
                    "alternative_explanation", "missing_evidence", "duplicate_source", "other")


class Objection(_Lenient):
    link_id: str = ""
    kind: ObjectionKind = "other"
    description: str
    cited_ids: List[str] = Field(default_factory=list)
    severity: Literal["low", "medium", "high"] = "medium"
    is_missing_evidence_only: bool = False     # true = absence of evidence, not evidence against
    requests_retrieval: bool = False
    retrieval_hint: str = ""

    # Large models vary the surface form; normalise rather than discard a whole review.
    @field_validator("kind", mode="before")
    @classmethod
    def _kind(cls, v: Any) -> Any:
        return v if v in _OBJECTION_KINDS else "other"

    @field_validator("severity", mode="before")
    @classmethod
    def _severity(cls, v: Any) -> Any:
        return v if v in ("low", "medium", "high") else "medium"

    @field_validator("cited_ids", mode="before")
    @classmethod
    def _ids(cls, v: Any) -> Any:
        return [v] if isinstance(v, str) else (v or [])


class SkepticReview(_Lenient):
    review_status: Literal["accepted", "accepted_with_objections", "needs_more_evidence", "rejected"]
    objections: List[Objection] = Field(default_factory=list)
    alternative_explanations: List[str] = Field(default_factory=list)
    suggested_retrieval: List[Any] = Field(default_factory=list)   # advisory only; the Planner decides what to retrieve


class Fact(_Lenient):
    statement: str
    source_ids: List[str] = Field(default_factory=list)


class Hypothesis(_Lenient):
    statement: str
    link_id: str = ""


class ReportOutput(_Lenient):
    title: str
    executive_summary: str
    facts: List[Fact] = Field(default_factory=list)
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    similarities: List[str] = Field(default_factory=list)
    differences: List[str] = Field(default_factory=list)
    contradictions_and_limitations: List[str] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    follow_up_actions: List[str] = Field(default_factory=list)


# ── compact evidence rendering (bounded; IDs always preserved) ──────────────
def _cut(v: Any, n: int) -> Any:
    return v[:n] if isinstance(v, str) else v


def compact_incident(r: Dict[str, Any]) -> Dict[str, Any]:
    keys = ("incident_id", "station_id", "crime_type", "location_id", "occurred_from", "occurred_to", "reported_at",
            "method_description", "property_involved", "status", "data_quality")
    return {k: r.get(k) for k in keys}


def compact_evidence(evidence: Dict[str, List[Dict[str, Any]]], per_source: int = 8) -> Dict[str, List[Dict[str, Any]]]:
    return {
        "forensic_reports": [
            {"evidence_report_id": r.get("evidence_report_id"), "evidence_item_id": r.get("evidence_item_id"),
             "incident_id": r.get("incident_id"), "location_id": r.get("location_id"), "evidence_type": r.get("evidence_type"),
             "result_status": r.get("result_status"), "description": _cut(r.get("description"), 220),
             "result_summary": _cut(r.get("result_summary"), 220), "limitations": r.get("limitations"), "link_basis": r.get("link_basis"),
             "data_quality": r.get("data_quality")} for r in evidence.get("forensic_reports", [])[:per_source]],
        "cctv_reports": [
            {"cctv_report_id": r.get("cctv_report_id"), "camera_id": r.get("camera_id"), "location_id": r.get("location_id"),
             "recorded_from": r.get("recorded_from"), "recorded_to": r.get("recorded_to"),
             "observed_entities": r.get("observed_entities"), "vehicle_description": r.get("vehicle_description"),
             "vehicle_color": r.get("vehicle_color"), "partial_plate": r.get("partial_plate"),
             "related_incident_ids": r.get("related_incident_ids"), "link_basis": r.get("link_basis"), "data_quality": r.get("data_quality")}
            for r in evidence.get("cctv_reports", [])[:per_source]],
        "witness_reports": [
            {"witness_report_id": r.get("witness_report_id"), "location_id": r.get("location_id"),
             "observed_from": r.get("observed_from"), "observation_text": _cut(r.get("observation_text"), 320),
             "vehicle_description": r.get("vehicle_description"), "contradiction_flags": r.get("contradiction_flags"),
             "related_incident_ids": r.get("related_incident_ids"), "link_basis": r.get("link_basis"), "data_quality": r.get("data_quality")}
            for r in evidence.get("witness_reports", [])[:per_source]],
        "newspaper_reports": [
            {"news_id": r.get("news_id"), "headline": r.get("headline"), "article_text": _cut(r.get("article_text"), 240),
             "related_incident_ids": r.get("related_incident_ids"), "link_basis": r.get("link_basis"), "source_reliability": r.get("source_reliability")}
            for r in evidence.get("newspaper_reports", [])[:per_source]],
    }


# ── prompts ──────────────────────────────────────────────────────────────────
JSON_ONLY = "Respond with one JSON object only. No prose, no markdown fences."

PLANNER_SYSTEM = (
    "You are the Investigator/Planner for a multi-station police intelligence system. You plan; you never "
    "retrieve data and you must never state that records were found - retrieval happens only when the "
    "Analyst executes your requests against the database. Similar descriptions do not establish a common "
    "offender; make no determination of guilt. " + JSON_ONLY
)

PLANNER_SCHEMA = """{
  "action": "retrieve" | "conclude" | "blocked",
  "rationale": "one or two sentences",
  "evidence_needed": ["attributes or record types still required"],
  "retrieval_requests": [
    {"kind": "keyword_search" | "by_incident_ids" | "related_records" | "location_window",
     "keywords": ["method or property terms"], "crime_types": ["BURGLARY"], "station_ids": ["NORTH","CENTRAL","RIVERSIDE"],
     "incident_ids": ["INC-..."], "date_from": null, "date_to": null, "reason": "why"}
  ],
  "outstanding_questions": ["open questions"]
}"""

FINDER_SYSTEM = (
    "You are the Finder / Evidence Analyst. You analyse ONLY the records supplied below; they came from the "
    "authoritative database. Never invent an ID, quotation, or attribute. Records with link_basis direct_reference cite the incident explicitly; location_proximity records only share a location and are context, not corroboration. Compare methods, timelines, locations "
    "and property; separate exact matches from semantic similarity; state differences and missing evidence as "
    "prominently as similarities. Similarity does not prove a common offender. " + JSON_ONLY
)

FINDER_SCHEMA = """{
  "links": [{
    "link_id": "LINK-01",
    "source_incident_id": "INC-...", "target_incident_id": "INC-...",
    "stations_involved": ["NORTH","CENTRAL"],
    "similarity_basis": "what is similar and why it matters",
    "shared_attributes": [{"attribute": "tool|vehicle_color|plate|method|property", "value": "text copied from the records",
                           "match_type": "exact" | "semantic", "source_ids": ["IDs of records containing the value"]}],
    "differences": ["..."], "missing_evidence": ["..."],
    "supporting_evidence_ids": ["CCTV-...","FOR-..."],
    "quotes": [{"source_id": "WIT-...", "text": "verbatim text from that record"}],
    "heuristic_score": 0.0-1.0, "score_note": "uncalibrated model estimate, not a probability"
  }],
  "withdrawn_link_ids": ["links you retract in light of objections"],
  "notes": ""
}"""

SKEPTIC_SYSTEM = (
    "You are the Skeptic / Contradiction Hunter. Your job is to find reasons the proposed links could be WRONG. "
    "You are not told whether the Finder is right and you must not defer to it. Check each cited ID against the "
    "records supplied; look for contradictions, incompatible timelines or locations, circular reasoning "
    "(similarity cited as proof of itself), unsupported claims, duplicate reports counted as independent "
    "corroboration, and innocent alternative explanations (coincidence, common practice, shared environment). "
    "Distinguish MISSING evidence (set is_missing_evidence_only=true) from evidence AGAINST a link. If more "
    "retrieval would resolve a doubt, say so with requests_retrieval=true. Cite only IDs present in the records. "
    + JSON_ONLY
)

SKEPTIC_SCHEMA = """{
  "review_status": "accepted" | "accepted_with_objections" | "needs_more_evidence" | "rejected",
  "objections": [{"link_id": "LINK-01", "kind": "contradiction|timeline|unsupported_claim|circular_reasoning|alternative_explanation|missing_evidence|duplicate_source|other",
                  "description": "...", "cited_ids": ["IDs"], "severity": "low|medium|high",
                  "is_missing_evidence_only": false, "requests_retrieval": false, "retrieval_hint": ""}],
  "alternative_explanations": ["..."],
  "suggested_retrieval": []
}"""

REPORTER_SYSTEM = (
    "You are the Reporter. Write for detectives using ONLY the validated state supplied. Every factual statement "
    "must cite source IDs present in that state. Label model-generated hypotheses as hypotheses. Do not hide, "
    "soften or drop contradictions or open Skeptic objections. Never present a heuristic score as a probability "
    "and never imply guilt. " + JSON_ONLY
)

REPORTER_SCHEMA = """{
  "title": "...", "executive_summary": "...",
  "facts": [{"statement": "source fact", "source_ids": ["IDs"]}],
  "hypotheses": [{"statement": "investigative possibility, not established", "link_id": "LINK-01"}],
  "similarities": ["..."], "differences": ["..."],
  "contradictions_and_limitations": ["..."], "unresolved_questions": ["..."], "follow_up_actions": ["..."]
}"""


@dataclass
class AgentResult:
    parsed: BaseModel
    calls: List[CallRecord] = field(default_factory=list)
    repaired: bool = False


def call_agent(registry: ModelRegistry, role: str, system: str, user: str, schema: Type[T],
               max_tokens: int = 1400, temperature: float = 0.2) -> AgentResult:
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    calls: List[CallRecord] = []
    last_err = "no JSON found in model output"
    for attempt in (1, 2):
        resp, rec = registry.generate(role, messages, max_tokens=max_tokens, temperature=temperature)
        calls.append(rec)
        data = extract_json_block(resp.content)
        if isinstance(data, list) and schema is FinderOutput:
            data = {"links": data}
        try:
            if not isinstance(data, dict):
                raise ValueError("output is not a JSON object")
            return AgentResult(schema.model_validate(data), calls, repaired=attempt == 2)
        except (ValidationError, ValueError) as exc:
            last_err = str(exc).replace("\n", " ")[:300]
            hint = ""
            if getattr(resp, "finish_reason", None) == "length":
                last_err += " [output was cut off at the token limit]"
                hint = " Your previous answer was cut off: be concise - at most 4 items per list and under 50 words per description."
            messages = [*messages, {"role": "assistant", "content": resp.content[:1500]},
                        {"role": "user", "content": f"That output was invalid ({last_err}). Return ONLY a valid JSON object matching the schema.{hint}"}]
    raise AgentOutputError(role, f"malformed output after repair: {last_err}", calls)


def run_planner(registry: ModelRegistry, user_prompt: str) -> AgentResult:
    return call_agent(registry, "planner", PLANNER_SYSTEM, f"{user_prompt}\n\nSchema:\n{PLANNER_SCHEMA}",
                      PlannerDecision, max_tokens=700, temperature=0.1)


def run_finder(registry: ModelRegistry, incidents: List[Dict[str, Any]], evidence: Dict[str, Any], objective: str,
               prior: Optional[Dict[str, Any]] = None) -> AgentResult:
    body = {"objective": objective, "incidents": [compact_incident(i) for i in incidents[:14]],
            "evidence": compact_evidence(evidence)}
    if prior:
        body["revision_context"] = prior
    user = (f"{json.dumps(body, default=str)}\n\nPropose cross-station links (different stations preferred) supported "
            f"by the records. If nothing is supportable, return an empty links list.\nSchema:\n{FINDER_SCHEMA}")
    return call_agent(registry, "finder", FINDER_SYSTEM, user, FinderOutput, max_tokens=3000, temperature=0.2)


def run_skeptic(registry: ModelRegistry, links: List[Dict[str, Any]], incidents: List[Dict[str, Any]],
                evidence: Dict[str, Any], verifier_summary: List[Dict[str, Any]]) -> AgentResult:
    # Heuristic scores are deliberately withheld so the Skeptic is not anchored by the Finder's confidence.
    blind = [{k: v for k, v in l.items() if k not in ("heuristic_score", "score_note")} for l in links]
    body = {"proposed_links": blind, "incidents": [compact_incident(i) for i in incidents[:14]],
            "evidence": compact_evidence(evidence), "deterministic_checks": verifier_summary}
    user = f"{json.dumps(body, default=str)}\n\nChallenge these links.\nSchema:\n{SKEPTIC_SCHEMA}"
    return call_agent(registry, "skeptic", SKEPTIC_SYSTEM, user, SkepticReview, max_tokens=3000, temperature=0.3)


def run_reporter(registry: ModelRegistry, validated_state: Dict[str, Any]) -> AgentResult:
    user = f"{json.dumps(validated_state, default=str)}\n\nWrite the report.\nSchema:\n{REPORTER_SCHEMA}"
    return call_agent(registry, "reporter", REPORTER_SYSTEM, user, ReportOutput, max_tokens=2400, temperature=0.2)
