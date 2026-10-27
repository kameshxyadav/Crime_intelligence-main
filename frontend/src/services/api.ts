import {
  AppHealthResponse,
  DashboardSummary,
  IncidentEvidenceResponse,
  IncidentFilters,
  IncidentListResponse,
  PoliceIncident,
  SourceListResponse,
  SourceRecordsResponse,
  ZetarisHealthResponse,
} from '../types';

const API_BASE = '/api';

// ── Inline types for auth and tips (not in shared types.ts) ──────────────
export interface UserProfile {
  user_id: string;
  name: string;
  role: string;
  badge_number: string | null;
  station: string | null;
  jurisdiction: string;
  email: string;
  token: string;
}

export interface TipResponse {
  tip_id: string;
  status: string;
  station_id: string;
  crime_type: string;
  guard_verdict: string;
  sanitization: Record<string, unknown>;
  submitted_at: string;
  message: string;
}

export interface TipRecord {
  tip_id: string;
  witness_report_id: string;
  station_id: string;
  crime_type: string;
  observation_text: string;
  vehicle_description: string | null;
  direction_of_travel: string | null;
  confidence_level: string;
  has_cctv_still: boolean;
  guard_verdict: string;
  sanitized_exif: boolean;
  ip_logged: boolean;
  submitted_at: string;
  // Officer Triage & Review Status
  review_status?: 'PENDING_REVIEW' | 'APPROVED' | 'ESCALATED_DISPATCH' | 'REJECTED';
  officer_notes?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  linked_incident_id?: string | null;
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    let errorMsg = `Request failed: ${res.status} ${res.statusText}`;
    try {
      const err = await res.json();
      if (err.detail) errorMsg = err.detail;
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getAppHealth: (): Promise<AppHealthResponse> =>
    fetchJson<AppHealthResponse>(`${API_BASE}/health`),

  getZetarisHealth: (): Promise<ZetarisHealthResponse> =>
    fetchJson<ZetarisHealthResponse>(`${API_BASE}/health/zetaris`),

  getDashboardSummary: (): Promise<DashboardSummary> =>
    fetchJson<DashboardSummary>(`${API_BASE}/dashboard/summary`),

  getIncidents: (filters: IncidentFilters): Promise<IncidentListResponse> => {
    const params = new URLSearchParams();
    params.set('page', String(filters.page || 1));
    params.set('page_size', String(filters.pageSize || 50));
    if (filters.search) params.set('search', filters.search);
    if (filters.station && filters.station !== 'ALL') params.set('station', filters.station);
    if (filters.crimeType && filters.crimeType !== 'ALL') params.set('crime_type', filters.crimeType);
    if (filters.status && filters.status !== 'ALL') params.set('status', filters.status);
    if (filters.dateFrom) params.set('date_from', filters.dateFrom);
    if (filters.dateTo) params.set('date_to', filters.dateTo);
    if (filters.sortBy) params.set('sort_by', filters.sortBy);
    if (typeof filters.sortDesc === 'boolean') params.set('sort_desc', String(filters.sortDesc));

    return fetchJson<IncidentListResponse>(`${API_BASE}/incidents?${params.toString()}`);
  },

  getIncidentById: (incidentId: string): Promise<PoliceIncident> =>
    fetchJson<PoliceIncident>(`${API_BASE}/incidents/${encodeURIComponent(incidentId)}`),

  getIncidentEvidence: (incidentId: string): Promise<IncidentEvidenceResponse> =>
    fetchJson<IncidentEvidenceResponse>(`${API_BASE}/incidents/${encodeURIComponent(incidentId)}/evidence`),

  getSources: (): Promise<SourceListResponse> =>
    fetchJson<SourceListResponse>(`${API_BASE}/sources`),

  getSourceRecords: (
    source: string,
    page: number = 1,
    pageSize: number = 25,
    search?: string
  ): Promise<SourceRecordsResponse> => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (search) params.set('search', search);
    return fetchJson<SourceRecordsResponse>(`${API_BASE}/sources/${encodeURIComponent(source)}/records?${params.toString()}`);
  },

  getSourceRecordById: (
    source: string,
    recordId: string
  ): Promise<{ source: string; record: Record<string, any>; data_mode: string }> =>
    fetchJson<{ source: string; record: Record<string, any>; data_mode: string }>(
      `${API_BASE}/sources/${encodeURIComponent(source)}/records/${encodeURIComponent(recordId)}`
    ),

  // ── Investigations & Agents ──────────────────────────────────────────────
  analyzeInvestigation: (req: import('../types').InvestigationRequest): Promise<import('../types').InvestigationResponse> =>
    postJson<import('../types').InvestigationResponse>(`${API_BASE}/investigations/analyze`, req),

  getSampleScenarios: (): Promise<import('../types').SampleScenarioMeta[]> =>
    fetchJson<import('../types').SampleScenarioMeta[]>(`${API_BASE}/investigations/samples`),

  getAIDiagnostic: (): Promise<import('../types').AIDiagnosticResponse> =>
    fetchJson<import('../types').AIDiagnosticResponse>(`${API_BASE}/ai/diagnostic`),

  getEngineHealth: (): Promise<import('../types').EngineHealthResponse> =>
    fetchJson<import('../types').EngineHealthResponse>(`${API_BASE}/engine/health`),

  // ── Auth / Role-Based Login ──────────────────────────────────────────────
  loginUser: (role: string): Promise<UserProfile> =>
    postJson<UserProfile>(`${API_BASE}/auth/login`, { role }),

  getDemoUsers: (): Promise<UserProfile[]> =>
    fetchJson<UserProfile[]>(`${API_BASE}/auth/users`),

  // ── Tips (Citizen Witness Portal) ───────────────────────────────────────
  submitTip: (data: {
    station_id: string;
    crime_type: string;
    observation_text: string;
    vehicle_description?: string;
    direction_of_travel?: string;
    has_cctv_still?: boolean;
    confidence_level?: string;
  }): Promise<TipResponse> =>
    postJson<TipResponse>(`${API_BASE}/tips/submit`, data),

  listTips: (): Promise<TipRecord[]> =>
    fetchJson<TipRecord[]>(`${API_BASE}/tips`),

  getTipById: (tipId: string): Promise<TipRecord> =>
    fetchJson<TipRecord>(`${API_BASE}/tips/${encodeURIComponent(tipId)}`),

  updateTipStatus: (
    tipId: string,
    action: {
      review_status: 'PENDING_REVIEW' | 'APPROVED' | 'ESCALATED_DISPATCH' | 'REJECTED';
      officer_notes?: string;
      reviewed_by?: string;
      linked_incident_id?: string;
    }
  ): Promise<TipRecord> =>
    postJson<TipRecord>(`${API_BASE}/tips/${encodeURIComponent(tipId)}/action`, action),
};

async function postJson<T>(url: string, data: any): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    let errorMsg = `Request failed: ${res.status} ${res.statusText}`;
    try {
      const err = await res.json();
      if (err.detail) errorMsg = err.detail;
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }
  return res.json() as Promise<T>;
}
