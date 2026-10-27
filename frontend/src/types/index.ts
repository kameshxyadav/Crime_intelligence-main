export type StationId = 'NORTH' | 'CENTRAL' | 'RIVERSIDE';

export type DataSource =
  | 'police_incidents'
  | 'newspaper_reports'
  | 'witness_reports'
  | 'cctv_reports'
  | 'forensic_reports';

export interface AppHealthResponse {
  status: string;
  version: string;
  environment: string;
}

export interface ZetarisHealthResponse {
  status: 'connected' | 'not_configured' | 'connection_failed' | 'query_failed';
  mode: 'zetaris_live' | 'local_fallback';
  configured: boolean;
  message: string;
  tables_verified?: string[];
  error_detail?: string;
}

export interface PaginationInfo {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface StationCount {
  station_id: string;
  count: number;
}

export interface CrimeTypeCount {
  crime_type: string;
  count: number;
}

export interface StatusCount {
  status: string;
  count: number;
}

export interface SourceCount {
  source: string;
  count: number;
}

export interface TimelineBucket {
  period: string;
  count: number;
}

export interface DashboardSummary {
  total_incidents: number;
  by_station: StationCount[];
  by_crime_type: CrimeTypeCount[];
  by_status: StatusCount[];
  by_source: SourceCount[];
  incident_timeline: TimelineBucket[];
  data_mode: 'zetaris_live' | 'local_fallback';
}

export interface PoliceIncident {
  incident_id: string;
  station_id: StationId;
  reported_at: string | null;
  occurred_from: string | null;
  occurred_to: string | null;
  crime_type: string;
  location_id: string;
  location_description: string;
  method_description: string;
  property_involved: string[];
  estimated_loss: number | null;
  status: 'OPEN' | 'UNDER_INVESTIGATION' | 'CLOSED' | 'UNRESOLVED';
  source_reference_ids: string[];
  data_quality: string;
}

export interface IncidentListResponse {
  items: PoliceIncident[];
  pagination: PaginationInfo;
  data_mode: 'zetaris_live' | 'local_fallback';
}

export interface SourceInfo {
  name: DataSource;
  label: string;
  record_count: number;
  primary_key_field: string;
  description: string;
}

export interface SourceListResponse {
  sources: SourceInfo[];
  data_mode: 'zetaris_live' | 'local_fallback';
}

export interface SourceRecordsResponse {
  source: string;
  items: Record<string, any>[];
  pagination: PaginationInfo;
  data_mode: 'zetaris_live' | 'local_fallback';
}

export interface EvidenceLink {
  source: string;
  record_id: string;
  link_type: 'direct_reference' | 'inferred_spatial_temporal';
  link_basis: string;
  record: Record<string, any>;
}

export interface IncidentEvidenceResponse {
  incident_id: string;
  incident: PoliceIncident | null;
  direct_links: EvidenceLink[];
  inferred_links: EvidenceLink[];
  data_mode: 'zetaris_live' | 'local_fallback';
}

export interface IncidentFilters {
  page: number;
  pageSize: number;
  search?: string;
  station?: string;
  crimeType?: string;
  status?: string;
  dateFrom?: string;
  dateTo?: string;
  sortBy?: string;
  sortDesc?: boolean;
}

export interface CandidateLink {
  link_id: string;
  source_incident_id: string;
  target_incident_id: string;
  stations_involved: string[];
  similarity_basis: string;
  confidence_score: number;
  confidence_rationale: string;
  supporting_evidence_ids: string[];
  contradictions: Array<{
    source_id?: string;
    description: string;
    flag?: string;
  }>;
  differences_or_inconsistencies?: string | null;
  // Multi-agent additions (absent on sample scenarios)
  withdrawn?: boolean;
  validation_status?: 'SUPPORTED' | 'WEAK' | 'UNSUPPORTED' | null;
  validation_explanation?: string | null;
  independent_source_count?: number | null;
  shared_attributes?: Array<{ attribute: string; value: string; match_type?: string; source_ids?: string[] }>;
  missing_evidence?: string[];
  rejected_ids?: string[];
}

export interface AgentSummary {
  agent: string;
  calls: number;
  requested_models: string[];
  reported_models: string[];
  providers: string[];
  fallback_used: boolean;
  fallback_reasons: string[];
  errors: string[];
  avg_latency_ms: number;
}

export interface EngineOperation {
  engine: string;
  op: string;
  status: string;
  latency_ms: number;
  detail?: Record<string, any>;
  error?: string | null;
}

export interface SkepticObjection {
  link_id?: string;
  kind: string;
  description: string;
  cited_ids: string[];
  severity: 'low' | 'medium' | 'high';
  is_missing_evidence_only: boolean;
  requests_retrieval: boolean;
  iteration: number;
  open: boolean;
  grounded: boolean;
  invalid_cited_ids: string[];
}

export interface IntegrationStatus {
  zetaris: {
    status: string;
    mode: string;
    tables_queried?: string[];
    note?: string;
  };
  nightshift_nemotron: {
    status: string;
    mode: string;
    model: string;
    provider?: string;
    winning_route?: any;
  };
  meterless_engine: {
    status: string;
    mode: string;
    feature: string;
    schema_version?: number;
    entities_count?: number;
    observations_count?: number;
    contradictions_count?: number;
  };
  meterless_engines?: Record<string, any>;
  model_registry?: Record<string, any>;
}

export interface InvestigationResponse {
  investigation_id: string;
  is_sample: boolean;
  data_mode: 'zetaris_live' | 'sample_mode';
  scenario_id?: string | null;
  title: string;
  query: string;
  stations_involved: string[];
  candidate_incidents: Record<string, any>[];
  supporting_evidence: {
    cctv_reports?: Record<string, any>[];
    witness_reports?: Record<string, any>[];
    forensic_reports?: Record<string, any>[];
    newspaper_reports?: Record<string, any>[];
  };
  candidate_links: CandidateLink[];
  contradictions_and_limitations: string[];
  unresolved_questions: string[];
  follow_up_actions: string[];
  executive_summary: string;
  integration_status: IntegrationStatus;
  retrieval_and_analysis_status: string;
  trace_file?: string | null;
  timestamp: number;
  elapsed_seconds?: number | null;
  // Multi-agent additions (null/absent for sample scenarios, which never ran live services)
  intent?: string | null;
  run_status?: string | null;
  stopping_reason?: string | null;
  iterations?: Array<Record<string, any>> | null;
  iterations_used?: number | null;
  agents?: AgentSummary[] | null;
  engine_operations?: EngineOperation[] | null;
  skeptic?: { review_status: string; history: string[]; objections: SkepticObjection[] } | null;
  validation_results?: Array<Record<string, any>> | null;
  report?: { facts: Array<{ statement: string; source_ids: string[] }>; hypotheses: Array<{ statement: string; link_id?: string }>;
             unverified_statements: Array<{ statement: string; reason: string }>; model_generated: boolean } | null;
  memory?: { retrieved: Array<{ id: string; content: string; stored_confidence: number; note: string }>; write: Record<string, any> } | null;
  partial_failures?: Array<{ component: string; message: string }> | null;
  counts?: { model_calls: number; sql_queries: number; iterations: number } | null;
  budget?: Record<string, any> | null;
  resume_hint?: string | null;
  clarification?: string | null;
}

export interface InvestigationRequest {
  query: string;
  incident_ids?: string[];
  station_ids?: string[];
  crime_type?: string;
  date_from?: string;
  date_to?: string;
  scenario_id?: string;
  sample_mode?: boolean;
  continue_from?: string;
}

export interface SampleScenarioMeta {
  scenario_id: string;
  title: string;
  query: string;
  target_stations: string[];
  crime_type: string;
  incidents_count: number;
  links_count: number;
}

export interface AIDiagnosticResponse {
  status: string;
  configured: boolean;
  message: string;
  provider?: string | null;
  model?: string | null;
  winning_route?: any;
  latency_ms?: number | null;
  error_detail?: string | null;
}

export interface EngineHealthResponse {
  status: string;
  engine: string;
  schema_version?: number | null;
  configured: boolean;
  engine_path: string;
  world_dir: string;
  message: string;
}
