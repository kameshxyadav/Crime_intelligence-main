"""
Pydantic response schemas for the Cross-Station Crime Intelligence API.
These models are safe to return to the frontend — no secrets, no ground-truth data.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, field_validator


# ── Enums ────────────────────────────────────────────────────────────────────


class DataSource(str, Enum):
    POLICE_INCIDENTS = "police_incidents"
    NEWSPAPER_REPORTS = "newspaper_reports"
    WITNESS_REPORTS = "witness_reports"
    CCTV_REPORTS = "cctv_reports"
    FORENSIC_REPORTS = "forensic_reports"


class StationId(str, Enum):
    NORTH = "NORTH"
    CENTRAL = "CENTRAL"
    RIVERSIDE = "RIVERSIDE"


# ── Health ───────────────────────────────────────────────────────────────────


class AppHealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class ZetarisHealthResponse(BaseModel):
    status: str
    """
    One of: 'connected', 'not_configured', 'connection_failed', 'query_failed'
    """
    mode: str
    """'zetaris_live' or 'local_fallback'"""
    configured: bool
    message: str
    tables_verified: Optional[list[str]] = None
    error_detail: Optional[str] = None


# ── Pagination ───────────────────────────────────────────────────────────────


class PaginationInfo(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel):
    items: list[Any]
    pagination: PaginationInfo
    data_mode: str
    """'zetaris_live' or 'local_fallback'"""


# ── Dashboard Summary ────────────────────────────────────────────────────────


class StationCount(BaseModel):
    station_id: str
    count: int


class CrimeTypeCount(BaseModel):
    crime_type: str
    count: int


class StatusCount(BaseModel):
    status: str
    count: int


class SourceCount(BaseModel):
    source: str
    count: int


class TimelineBucket(BaseModel):
    period: str       # ISO 8601 month string: e.g. "2025-03"
    count: int


class DashboardSummary(BaseModel):
    total_incidents: int
    by_station: list[StationCount]
    by_crime_type: list[CrimeTypeCount]
    by_status: list[StatusCount]
    by_source: list[SourceCount]
    incident_timeline: list[TimelineBucket]
    data_mode: str


# ── Police Incidents ─────────────────────────────────────────────────────────


class PoliceIncident(BaseModel):
    incident_id: str
    station_id: str
    reported_at: Optional[str]
    occurred_from: Optional[str]
    occurred_to: Optional[str]
    crime_type: str
    location_id: str
    location_description: str
    method_description: str
    property_involved: list[str]
    estimated_loss: Optional[float]
    status: str
    source_reference_ids: list[str]
    data_quality: str


class IncidentListResponse(BaseModel):
    items: list[PoliceIncident]
    pagination: PaginationInfo
    data_mode: str


# ── Source Record schemas ─────────────────────────────────────────────────────


class NewspaperReport(BaseModel):
    news_id: str
    publication_name: str
    published_at: Optional[str]
    headline: str
    article_text: str
    mentioned_date_from: Optional[str]
    mentioned_date_to: Optional[str]
    mentioned_location_ids: list[str]
    crime_labels: list[str]
    mentioned_property: list[str]
    related_incident_ids: list[str]
    source_reliability: str
    data_quality: str


class WitnessReport(BaseModel):
    witness_report_id: str
    submitted_at: Optional[str]
    observed_from: Optional[str]
    observed_to: Optional[str]
    location_id: str
    observation_text: str
    observed_entities: list[str]
    vehicle_description: Optional[str]
    direction_of_travel: Optional[str]
    confidence_level: str
    related_incident_ids: list[str]
    contradiction_flags: list[str]
    data_quality: str


class CCTVReport(BaseModel):
    cctv_report_id: str
    camera_id: str
    location_id: str
    recorded_from: Optional[str]
    recorded_to: Optional[str]
    observed_entities: list[str]
    vehicle_description: Optional[str]
    vehicle_color: Optional[str]
    partial_plate: Optional[str]
    movement_description: str
    image_quality: str
    observation_confidence: float
    related_incident_ids: list[str]
    data_quality: str


class ForensicReport(BaseModel):
    evidence_report_id: str
    incident_id: Optional[str]
    evidence_item_id: str
    collected_at: Optional[str]
    location_id: str
    evidence_type: str
    description: str
    examination_method: str
    result_summary: str
    result_status: str
    confidence_level: str
    compared_evidence_ids: list[str]
    limitations: Optional[str]
    data_quality: str


# ── Source listing ───────────────────────────────────────────────────────────


class SourceInfo(BaseModel):
    name: str
    label: str
    record_count: int
    primary_key_field: str
    description: str


class SourceListResponse(BaseModel):
    sources: list[SourceInfo]
    data_mode: str


class SourceRecordsResponse(BaseModel):
    source: str
    items: list[dict]
    pagination: PaginationInfo
    data_mode: str


# ── Cross-source evidence ─────────────────────────────────────────────────────


class EvidenceLink(BaseModel):
    source: str
    record_id: str
    link_type: str
    """'direct_reference' or 'inferred_spatial_temporal'"""
    link_basis: str
    record: dict


class IncidentEvidenceResponse(BaseModel):
    incident_id: str
    incident: Optional[PoliceIncident]
    direct_links: list[EvidenceLink]
    inferred_links: list[EvidenceLink]
    data_mode: str
    caveat: str


# ── Investigations & Agents ──────────────────────────────────────────────────


class InvestigationRequest(BaseModel):
    query: str
    incident_ids: Optional[list[str]] = None
    station_ids: Optional[list[str]] = None
    crime_type: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    scenario_id: Optional[str] = None
    sample_mode: Optional[bool] = None
    continue_from: Optional[str] = None   # resume a saved, unfinished investigation


class CandidateLink(BaseModel):
    link_id: str
    source_incident_id: str
    target_incident_id: str
    stations_involved: list[str]
    similarity_basis: str
    confidence_score: float
    confidence_rationale: str
    supporting_evidence_ids: list[str] = []
    contradictions: list[dict] = []
    differences_or_inconsistencies: Optional[str] = None
    # Multi-agent additions (all optional so sample/legacy results stay valid)
    withdrawn: bool = False
    validation_status: Optional[str] = None            # SUPPORTED | WEAK | UNSUPPORTED (deterministic verifier)
    validation_explanation: Optional[str] = None
    independent_source_count: Optional[int] = None
    shared_attributes: list[dict] = []
    missing_evidence: list[str] = []
    revision: Optional[int] = None
    rejected_ids: list[str] = []


class InvestigationResponse(BaseModel):
    investigation_id: str
    is_sample: bool
    data_mode: str
    scenario_id: Optional[str] = None
    title: str
    query: str
    stations_involved: list[str]
    candidate_incidents: list[dict]
    supporting_evidence: dict[str, list[dict]]
    candidate_links: list[CandidateLink]
    contradictions_and_limitations: list[str]
    unresolved_questions: list[str]
    follow_up_actions: list[str]
    executive_summary: str
    integration_status: dict[str, Any]
    retrieval_and_analysis_status: str
    trace_file: Optional[str] = None
    timestamp: float
    elapsed_seconds: Optional[float] = None
    # Multi-agent additions (None for sample scenarios, which never ran live services)
    intent: Optional[str] = None
    route: Optional[dict] = None
    run_status: Optional[str] = None
    stopping_reason: Optional[str] = None
    iterations: Optional[list[dict]] = None
    iterations_used: Optional[int] = None
    agents: Optional[list[dict]] = None
    model_calls: Optional[list[dict]] = None
    engine_operations: Optional[list[dict]] = None
    skeptic: Optional[dict] = None
    validation_results: Optional[list[dict]] = None
    report: Optional[dict] = None
    memory: Optional[dict] = None
    partial_failures: Optional[list[dict]] = None
    counts: Optional[dict] = None
    budget: Optional[dict] = None
    resume_hint: Optional[str] = None
    clarification: Optional[str] = None


class AIDiagnosticResponse(BaseModel):
    status: str
    configured: bool
    message: str
    provider: Optional[str] = None
    model: Optional[str] = None
    winning_route: Optional[dict] = None
    latency_ms: Optional[float] = None
    error_detail: Optional[str] = None


class EngineHealthResponse(BaseModel):
    status: str
    engine: str
    schema_version: Optional[int] = None
    configured: bool
    engine_path: str
    world_dir: str
    message: str
