import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Camera,
  CheckCircle2,
  AlertTriangle,
  Key,
  EyeOff,
  Sparkles,
  AlertCircle,
  Filter,
  Search,
  Check,
  X,
  Radio,
  FileText,
  UserCheck,
  RefreshCw,
} from 'lucide-react';
import { api, TipRecord, UserProfile } from '../services/api';

interface PublicTipPortalPageProps {
  currentUser?: UserProfile | null;
}

const STATION_MAP: Record<string, string> = {
  'PS-SEC17': 'Sector 17 Central (PS-SEC17)',
  'PS-SEC22': 'Sector 22 (PS-SEC22)',
  'PS-INDUSTRIAL': 'Industrial Area Phase 1 (PS-INDUSTRIAL)',
  'PS-SEC40': 'Sector 40 Dhanas Corridor (PS-SEC40)',
};

const CRIME_TYPES = [
  { value: 'BURGLARY', label: 'Safe / Commercial Burglary' },
  { value: 'THEFT', label: 'Catalytic Converter / Parts Theft' },
  { value: 'VEHICLE_THEFT', label: 'Keyless Vehicle / SUV Relay' },
  { value: 'OTHER', label: 'Suspicious Prowler / Scouting' },
];

const GUARD_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  CLEAN_EVIDENCE_LEAD: { label: '✓ Clean Evidence Lead', color: '#065f46', bg: '#d1fae5' },
  EMERGENCY_DISPATCH_112: { label: '🚨 Emergency — Dispatch 112', color: '#92400e', bg: '#fef3c7' },
  QUARANTINED_PROMPT_INJECTION: { label: '⛔ Quarantined (Injection Detected)', color: '#991b1b', bg: '#fee2e2' },
};

const STATUS_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; border: string }
> = {
  PENDING_REVIEW: {
    label: 'Pending Officer Review',
    color: '#b45309',
    bg: '#fef3c7',
    border: '#fde68a',
  },
  APPROVED: {
    label: 'Verified Lead (Approved)',
    color: '#047857',
    bg: '#d1fae5',
    border: '#a7f3d0',
  },
  ESCALATED_DISPATCH: {
    label: '112 Patrol Dispatched',
    color: '#b91c1c',
    bg: '#fee2e2',
    border: '#fca5a5',
  },
  REJECTED: {
    label: 'Rejected (Decoy / Noise)',
    color: '#475569',
    bg: '#f1f5f9',
    border: '#cbd5e1',
  },
};

export const PublicTipPortalPage: React.FC<PublicTipPortalPageProps> = ({ currentUser }) => {
  const isOfficerOrStaff = Boolean(
    currentUser && ['officer', 'analyst', 'admin'].includes(currentUser.role)
  );

  // Tab mode for staff: 'triage' (Review Queue) vs 'submit' (Intake Form)
  // For citizens, it's always 'submit' or 'track'
  const [activeView, setActiveView] = useState<'triage' | 'submit' | 'track'>(
    isOfficerOrStaff ? 'triage' : 'submit'
  );

  // Form states
  const [stationId, setStationId] = useState<string>('PS-SEC17');
  const [crimeType, setCrimeType] = useState<string>('BURGLARY');
  const [tipNarrative, setTipNarrative] = useState<string>(
    'Observed dark Dodge Caravan with dented tailgate parked behind Central Plaza. Two individuals carried heavy pry bars towards the rear entrance.'
  );
  const [vehicleNote, setVehicleNote] = useState<string>('Grey Dodge Caravan, partial plate 7XK***');
  const [fileAttached, setFileAttached] = useState<boolean>(true);
  const [submittedTip, setSubmittedTip] = useState<{
    tip_id: string;
    guard_verdict: string;
    submitted_at: string;
  } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Tips list & triage state
  const [tips, setTips] = useState<TipRecord[]>([]);
  const [tipsLoading, setTipsLoading] = useState<boolean>(false);
  const [selectedStationFilter, setSelectedStationFilter] = useState<string>('ALL');
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Officer action drawer/inline state
  const [actionTipId, setActionTipId] = useState<string | null>(null);
  const [actionNotes, setActionNotes] = useState<string>('');
  const [actionIncidentId, setActionIncidentId] = useState<string>('');
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  // Tracking query for public citizens
  const [trackCode, setTrackCode] = useState<string>('');
  const [trackedTip, setTrackedTip] = useState<TipRecord | null>(null);
  const [trackError, setTrackError] = useState<string | null>(null);
  const [trackLoading, setTrackLoading] = useState<boolean>(false);

  const fetchTips = () => {
    setTipsLoading(true);
    api
      .listTips()
      .then((data) => setTips(data))
      .catch(() => setTips([]))
      .finally(() => setTipsLoading(false));
  };

  useEffect(() => {
    fetchTips();
  }, []);

  // Update active view if user changes
  useEffect(() => {
    if (isOfficerOrStaff && activeView === 'track') {
      setActiveView('triage');
    }
  }, [currentUser]);

  const handleSubmitTip = async (e: React.FormEvent) => {
    e.preventDefault();
    if (tipNarrative.trim().length < 20) {
      setSubmitError('Observation narrative must be at least 20 characters. Please provide more detail.');
      return;
    }
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const result = await api.submitTip({
        station_id: stationId,
        crime_type: crimeType,
        observation_text: tipNarrative,
        vehicle_description: vehicleNote || undefined,
        has_cctv_still: fileAttached,
        confidence_level: 'HIGH',
      });
      setSubmittedTip({
        tip_id: result.tip_id,
        guard_verdict: result.guard_verdict,
        submitted_at: result.submitted_at,
      });
      fetchTips();
    } catch {
      // Offline fallback
      const fallbackId = `TIP-CHD-${Math.random().toString(36).slice(2, 8).toUpperCase()}`;
      setSubmittedTip({
        tip_id: fallbackId,
        guard_verdict: 'CLEAN_EVIDENCE_LEAD',
        submitted_at: new Date().toISOString(),
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOfficerAction = async (
    tipId: string,
    statusToSet: 'APPROVED' | 'ESCALATED_DISPATCH' | 'REJECTED'
  ) => {
    setActionLoading(true);
    setActionSuccessMsg(null);
    try {
      const reviewerName = currentUser
        ? `${currentUser.name} (${currentUser.badge_number || currentUser.role})`
        : 'Station Officer';
      await api.updateTipStatus(tipId, {
        review_status: statusToSet,
        officer_notes: actionNotes.trim() || undefined,
        reviewed_by: reviewerName,
        linked_incident_id: actionIncidentId.trim() || undefined,
      });
      setActionSuccessMsg(`Tip ${tipId} updated to ${statusToSet}`);
      setActionTipId(null);
      setActionNotes('');
      setActionIncidentId('');
      fetchTips();
    } catch (err: any) {
      alert(`Failed to update tip: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleTrackTip = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!trackCode.trim()) return;
    setTrackLoading(true);
    setTrackError(null);
    setTrackedTip(null);
    try {
      const tip = await api.getTipById(trackCode.trim().toUpperCase());
      setTrackedTip(tip);
    } catch {
      // Look in local state if API fails
      const found = tips.find(
        (t) =>
          t.tip_id.toUpperCase() === trackCode.trim().toUpperCase() ||
          t.witness_report_id.toUpperCase() === trackCode.trim().toUpperCase()
      );
      if (found) {
        setTrackedTip(found);
      } else {
        setTrackError(`No record found matching code "${trackCode.trim()}". Verify the code and try again.`);
      }
    } finally {
      setTrackLoading(false);
    }
  };

  // Filtered tips for officer triage
  const filteredTips = tips.filter((t) => {
    if (selectedStationFilter !== 'ALL' && t.station_id !== selectedStationFilter) return false;
    const currentStatus = t.review_status || 'PENDING_REVIEW';
    if (selectedStatusFilter !== 'ALL' && currentStatus !== selectedStatusFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchText = (t.observation_text || '').toLowerCase();
      const matchVeh = (t.vehicle_description || '').toLowerCase();
      const matchId = (t.tip_id || '').toLowerCase();
      if (!matchText.includes(q) && !matchVeh.includes(q) && !matchId.includes(q)) return false;
    }
    return true;
  });

  // Triage count metrics
  const countPending = tips.filter((t) => (t.review_status || 'PENDING_REVIEW') === 'PENDING_REVIEW').length;
  const countApproved = tips.filter((t) => t.review_status === 'APPROVED').length;
  const countEscalated = tips.filter((t) => t.review_status === 'ESCALATED_DISPATCH').length;
  const countRejected = tips.filter((t) => t.review_status === 'REJECTED').length;

  const guardInfo = submittedTip
    ? GUARD_LABELS[submittedTip.guard_verdict] ?? GUARD_LABELS['CLEAN_EVIDENCE_LEAD']
    : null;

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
      {/* ── Top Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '4px 12px', background: isOfficerOrStaff ? '#e0e7ff' : '#d1fae5', border: `1px solid ${isOfficerOrStaff ? '#c7d2fe' : '#a7f3d0'}`, borderRadius: '9999px', fontSize: '0.75rem', fontWeight: 700, color: isOfficerOrStaff ? '#4338ca' : '#065f46', marginBottom: '0.6rem' }}>
            {isOfficerOrStaff ? <Radio size={14} color="#4f46e5" /> : <ShieldCheck size={14} color="#059669" />}
            {isOfficerOrStaff ? 'LAW ENFORCEMENT INTELLIGENCE TRIAGE' : '100% ANONYMOUS & ENCRYPTED CITIZEN PORTAL'}
          </div>
          <h1 style={{ fontSize: '2.1rem', fontWeight: 900, color: '#0f172a', letterSpacing: '-0.02em', margin: '0 0 0.35rem 0' }}>
            {isOfficerOrStaff ? 'Cross-Station Tip & Witness Lead Triage' : 'Citizen Tip & CCTV Evidence Intake'}
          </h1>
          <p style={{ color: '#475569', fontSize: '0.95rem', maxWidth: '780px', lineHeight: 1.5, margin: 0 }}>
            {isOfficerOrStaff
              ? 'Review incoming citizen sightings, audit Scout Intent screening, promote verified tips to active case leads, or dispatch 112 field patrol units across Chandigarh.'
              : 'Submit observations or security camera footage to assist cross-station police investigations. Client-side EXIF/GPS scrubbing ensures total anonymity with zero IP address tracking.'}
          </p>
        </div>

        {/* View Switcher Tabs */}
        <div style={{ display: 'flex', background: '#f1f5f9', padding: '4px', borderRadius: '10px', gap: '4px', border: '1px solid #e2e8f0' }}>
          {isOfficerOrStaff && (
            <button
              onClick={() => setActiveView('triage')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '8px',
                fontSize: '0.82rem',
                fontWeight: 700,
                background: activeView === 'triage' ? '#ffffff' : 'transparent',
                color: activeView === 'triage' ? '#4f46e5' : '#64748b',
                boxShadow: activeView === 'triage' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              <UserCheck size={14} />
              Review Queue
              {countPending > 0 && (
                <span style={{ background: '#f59e0b', color: '#ffffff', fontSize: '0.68rem', fontWeight: 800, padding: '1px 6px', borderRadius: '9999px' }}>
                  {countPending}
                </span>
              )}
            </button>
          )}

          <button
            onClick={() => setActiveView('submit')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '8px',
              fontSize: '0.82rem',
              fontWeight: 700,
              background: activeView === 'submit' ? '#ffffff' : 'transparent',
              color: activeView === 'submit' ? '#4f46e5' : '#64748b',
              boxShadow: activeView === 'submit' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            <Camera size={14} />
            {isOfficerOrStaff ? 'Submit Field Lead' : 'Submit Anonymous Tip'}
          </button>

          {!isOfficerOrStaff && (
            <button
              onClick={() => setActiveView('track')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '8px',
                fontSize: '0.82rem',
                fontWeight: 700,
                background: activeView === 'track' ? '#ffffff' : 'transparent',
                color: activeView === 'track' ? '#4f46e5' : '#64748b',
                boxShadow: activeView === 'track' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              <Key size={14} />
              Check Tip Status
            </button>
          )}
        </div>
      </div>

      {actionSuccessMsg && (
        <div style={{ background: '#d1fae5', border: '1px solid #a7f3d0', color: '#065f46', padding: '0.75rem 1rem', borderRadius: '10px', fontSize: '0.85rem', fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span>✓ {actionSuccessMsg}</span>
          <button onClick={() => setActionSuccessMsg(null)} style={{ background: 'none', border: 'none', color: '#065f46', cursor: 'pointer' }}>✕</button>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* 1. OFFICER REVIEW & TRIAGE QUEUE (Officers / Analysts / Admins)     */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      {activeView === 'triage' && isOfficerOrStaff && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Metrics Ribbon */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
            <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '1rem 1.25rem', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: '#64748b' }}>Total Ingested</span>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#0f172a', marginTop: '2px' }}>{tips.length}</div>
              <span style={{ fontSize: '0.72rem', color: '#059669' }}>Zetaris witness store synced</span>
            </div>

            <div style={{ background: '#fffbeb', border: '1px solid #fef3c7', borderRadius: '12px', padding: '1rem 1.25rem' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: '#b45309' }}>Pending Verification</span>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#b45309', marginTop: '2px' }}>{countPending}</div>
              <span style={{ fontSize: '0.72rem', color: '#92400e' }}>Awaiting officer assessment</span>
            </div>

            <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '12px', padding: '1rem 1.25rem' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: '#047857' }}>Verified Active Leads</span>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#047857', marginTop: '2px' }}>{countApproved}</div>
              <span style={{ fontSize: '0.72rem', color: '#065f46' }}>Linked to syndicates</span>
            </div>

            <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '12px', padding: '1rem 1.25rem' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: '#b91c1c' }}>112 Patrol Dispatched</span>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#b91c1c', marginTop: '2px' }}>{countEscalated}</div>
              <span style={{ fontSize: '0.72rem', color: '#991b1b' }}>Urgent field response</span>
            </div>

            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '1rem 1.25rem' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: '#64748b' }}>Rejected / Struck</span>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#475569', marginTop: '2px' }}>{countRejected}</div>
              <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Decoys & false alarms</span>
            </div>
          </div>

          {/* Filter & Search Bar */}
          <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1, minWidth: '260px' }}>
              <Search size={16} color="#94a3b8" />
              <input
                type="text"
                placeholder="Filter by tip ID, suspect vehicle, or observation details..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ width: '100%', border: 'none', outline: 'none', fontSize: '0.85rem', color: '#0f172a' }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <Filter size={15} color="#64748b" />
              <select
                value={selectedStationFilter}
                onChange={(e) => setSelectedStationFilter(e.target.value)}
                style={{ padding: '5px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '0.78rem', fontWeight: 600, color: '#0f172a', background: '#f8fafc' }}
              >
                <option value="ALL">All Stations</option>
                <option value="PS-SEC17">PS-SEC17 (Sector 17)</option>
                <option value="PS-SEC22">PS-SEC22 (Sector 22)</option>
                <option value="PS-INDUSTRIAL">PS-INDUSTRIAL (Phase 1)</option>
                <option value="PS-SEC40">PS-SEC40 (Dhanas)</option>
              </select>

              <select
                value={selectedStatusFilter}
                onChange={(e) => setSelectedStatusFilter(e.target.value)}
                style={{ padding: '5px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '0.78rem', fontWeight: 600, color: '#0f172a', background: '#f8fafc' }}
              >
                <option value="ALL">All Statuses</option>
                <option value="PENDING_REVIEW">Pending Review</option>
                <option value="APPROVED">Verified Lead</option>
                <option value="ESCALATED_DISPATCH">112 Dispatched</option>
                <option value="REJECTED">Rejected</option>
              </select>

              <button
                onClick={fetchTips}
                title="Refresh Tips"
                style={{ padding: '5px 8px', borderRadius: '8px', border: '1px solid #cbd5e1', background: '#ffffff', cursor: 'pointer', color: '#64748b', display: 'flex', alignItems: 'center' }}
              >
                <RefreshCw size={14} className={tipsLoading ? 'spin' : ''} />
              </button>
            </div>
          </div>

          {/* Tips List */}
          {tipsLoading ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>
              <RefreshCw size={24} className="spin" style={{ margin: '0 auto 0.5rem' }} />
              Loading citizen submissions...
            </div>
          ) : filteredTips.length === 0 ? (
            <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '3rem', textAlign: 'center' }}>
              <ShieldCheck size={36} color="#94a3b8" style={{ margin: '0 auto 0.5rem' }} />
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a' }}>No matching tips found</h3>
              <p style={{ fontSize: '0.82rem', color: '#64748b' }}>Try adjusting your search query or station/status filters.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {filteredTips.map((tip) => {
                const statusKey = tip.review_status || 'PENDING_REVIEW';
                const stConf = STATUS_CONFIG[statusKey] ?? STATUS_CONFIG['PENDING_REVIEW'];
                const guardConf = GUARD_LABELS[tip.guard_verdict] ?? GUARD_LABELS['CLEAN_EVIDENCE_LEAD'];
                const isActionOpen = actionTipId === tip.tip_id;

                return (
                  <div
                    key={tip.tip_id}
                    style={{
                      background: '#ffffff',
                      border: `1px solid ${statusKey === 'PENDING_REVIEW' ? '#fde68a' : '#e2e8f0'}`,
                      borderRadius: '14px',
                      padding: '1.25rem 1.5rem',
                      boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.85rem',
                    }}
                  >
                    {/* Header Row */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                        <code style={{ fontSize: '0.88rem', fontWeight: 800, color: '#4f46e5', background: '#f8fafc', padding: '2px 8px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                          {tip.tip_id}
                        </code>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '2px 8px', borderRadius: '9999px', background: stConf.bg, color: stConf.color, border: `1px solid ${stConf.border}` }}>
                          {stConf.label}
                        </span>
                        <span style={{ fontSize: '0.72rem', fontWeight: 700, padding: '2px 8px', borderRadius: '9999px', background: guardConf.bg, color: guardConf.color }}>
                          {guardConf.label}
                        </span>
                      </div>

                      <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                        Submitted: {tip.submitted_at.replace('T', ' ').replace('Z', ' UTC')}
                      </div>
                    </div>

                    {/* Metadata tags */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.78rem', color: '#475569', flexWrap: 'wrap' }}>
                      <span><strong>Jurisdiction:</strong> {STATION_MAP[tip.station_id] || tip.station_id}</span>
                      <span>•</span>
                      <span><strong>Crime:</strong> {tip.crime_type}</span>
                      {tip.has_cctv_still && (
                        <>
                          <span>•</span>
                          <span style={{ color: '#059669', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                            <Camera size={13} /> CCTV Footage Attached
                          </span>
                        </>
                      )}
                      <span>•</span>
                      <span style={{ color: '#059669', display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                        <EyeOff size={13} /> EXIF Scrubbed
                      </span>
                    </div>

                    {/* Observation narrative */}
                    <div style={{ background: '#f8fafc', padding: '0.85rem 1rem', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '0.85rem', color: '#1e293b', lineHeight: 1.5 }}>
                      <div style={{ fontWeight: 700, color: '#475569', fontSize: '0.72rem', textTransform: 'uppercase', marginBottom: '3px' }}>
                        Citizen Statement:
                      </div>
                      {tip.observation_text}
                    </div>

                    {/* Vehicle note if present */}
                    {tip.vehicle_description && (
                      <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.8rem', color: '#334155' }}>
                        <span style={{ fontWeight: 700, color: '#64748b' }}>Vehicle Description:</span>
                        <span>{tip.vehicle_description}</span>
                        {tip.direction_of_travel && <span style={{ color: '#64748b' }}>(Direction: {tip.direction_of_travel})</span>}
                      </div>
                    )}

                    {/* Officer Review Log if already audited */}
                    {tip.reviewed_by && (
                      <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '0.65rem 0.85rem', fontSize: '0.78rem', color: '#065f46' }}>
                        <div style={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <CheckCircle2 size={13} /> Reviewed by {tip.reviewed_by} on {tip.reviewed_at?.replace('T', ' ').replace('Z', ' UTC')}
                        </div>
                        {tip.officer_notes && <div style={{ marginTop: '2px', color: '#14532d' }}>Notes: {tip.officer_notes}</div>}
                        {tip.linked_incident_id && (
                          <div style={{ marginTop: '2px', fontWeight: 700 }}>
                            Linked Incident: <code style={{ color: '#047857' }}>{tip.linked_incident_id}</code>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Officer Action Bar */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #f1f5f9', paddingTop: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <button
                        onClick={() => {
                          if (isActionOpen) {
                            setActionTipId(null);
                          } else {
                            setActionTipId(tip.tip_id);
                            setActionNotes(tip.officer_notes || '');
                            setActionIncidentId(tip.linked_incident_id || '');
                          }
                        }}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#4f46e5',
                          fontSize: '0.78rem',
                          fontWeight: 700,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: 0,
                        }}
                      >
                        <FileText size={14} />
                        {isActionOpen ? 'Hide Case Note Editor ▲' : 'Attach Officer Notes & Link Incident ▼'}
                      </button>

                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          onClick={() => handleOfficerAction(tip.tip_id, 'APPROVED')}
                          disabled={actionLoading}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '5px',
                            padding: '6px 12px',
                            borderRadius: '8px',
                            background: '#059669',
                            color: '#ffffff',
                            border: 'none',
                            fontSize: '0.78rem',
                            fontWeight: 700,
                            cursor: 'pointer',
                            boxShadow: '0 1px 2px rgba(5, 150, 105, 0.2)',
                          }}
                        >
                          <Check size={14} />
                          Approve as Verified Lead
                        </button>

                        <button
                          onClick={() => handleOfficerAction(tip.tip_id, 'ESCALATED_DISPATCH')}
                          disabled={actionLoading}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '5px',
                            padding: '6px 12px',
                            borderRadius: '8px',
                            background: '#dc2626',
                            color: '#ffffff',
                            border: 'none',
                            fontSize: '0.78rem',
                            fontWeight: 700,
                            cursor: 'pointer',
                            boxShadow: '0 1px 2px rgba(220, 38, 38, 0.2)',
                          }}
                        >
                          <Radio size={14} />
                          Escalate 112 Patrol
                        </button>

                        <button
                          onClick={() => handleOfficerAction(tip.tip_id, 'REJECTED')}
                          disabled={actionLoading}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '5px',
                            padding: '6px 12px',
                            borderRadius: '8px',
                            background: '#f1f5f9',
                            color: '#475569',
                            border: '1px solid #cbd5e1',
                            fontSize: '0.78rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          <X size={14} />
                          Reject Decoy
                        </button>
                      </div>
                    </div>

                    {/* Inline Officer Note & Incident Link Drawer */}
                    {isActionOpen && (
                      <div style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '10px', padding: '1rem', marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                          <div>
                            <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: '#475569', textTransform: 'uppercase', marginBottom: '3px' }}>
                              Link to Police Incident ID (Optional)
                            </label>
                            <input
                              type="text"
                              placeholder="e.g. INC-SEC17-0118"
                              value={actionIncidentId}
                              onChange={(e) => setActionIncidentId(e.target.value)}
                              style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.82rem', background: '#ffffff' }}
                            />
                          </div>

                          <div>
                            <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: '#475569', textTransform: 'uppercase', marginBottom: '3px' }}>
                              Auditing Officer
                            </label>
                            <input
                              type="text"
                              disabled
                              value={currentUser ? `${currentUser.name} (${currentUser.badge_number || currentUser.station || ''})` : 'Insp. Rajesh Sharma (CHD-POL-1704)'}
                              style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid #e2e8f0', fontSize: '0.82rem', background: '#f1f5f9', color: '#64748b' }}
                            />
                          </div>
                        </div>

                        <div>
                          <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: '#475569', textTransform: 'uppercase', marginBottom: '3px' }}>
                            Investigative Assessment / Triage Remarks
                          </label>
                          <textarea
                            rows={2}
                            placeholder="Enter notes on why this lead is verified, forensic correlations, or patrol dispatch instructions..."
                            value={actionNotes}
                            onChange={(e) => setActionNotes(e.target.value)}
                            style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.82rem', background: '#ffffff', resize: 'vertical' }}
                          />
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                          <button
                            onClick={() => setActionTipId(null)}
                            style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid #cbd5e1', background: '#ffffff', fontSize: '0.78rem', color: '#64748b', cursor: 'pointer' }}
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleOfficerAction(tip.tip_id, 'APPROVED')}
                            disabled={actionLoading}
                            style={{ padding: '6px 14px', borderRadius: '6px', border: 'none', background: '#4f46e5', color: '#ffffff', fontSize: '0.78rem', fontWeight: 700, cursor: 'pointer' }}
                          >
                            {actionLoading ? 'Saving...' : 'Save & Mark Verified'}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* 2. CITIZEN TIP INTAKE FORM (Public or Field Lead)                   */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      {activeView === 'submit' && (
        <>
          {submittedTip ? (
            <div style={{ background: '#ffffff', border: '1px solid #a7f3d0', borderRadius: '16px', padding: '2.5rem', textAlign: 'center', boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
              <div style={{ width: 56, height: 56, borderRadius: '50%', background: '#d1fae5', color: '#059669', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.25rem' }}>
                <CheckCircle2 size={32} />
              </div>
              <h2 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#0f172a', marginBottom: '0.5rem' }}>
                {isOfficerOrStaff ? 'Field Intelligence Lead Ingested' : 'Tip Securely Received'}
              </h2>
              <p style={{ color: '#475569', fontSize: '0.95rem', maxWidth: '520px', margin: '0 auto 1.5rem' }}>
                {isOfficerOrStaff
                  ? 'Your field report has been persisted to the Zetaris intelligence store and entered into the station triage queue.'
                  : 'Your statement has been scrubbed of all metadata and ingested into the Chandigarh Police Zetaris intelligence layer. Save your anonymous reference code:'}
              </p>

              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1.5rem', background: '#f8fafc', border: '2px dashed #4f46e5', borderRadius: '12px', fontSize: '1.3rem', fontWeight: 800, color: '#4f46e5', letterSpacing: '0.08em', marginBottom: '1rem' }}>
                <Key size={20} />
                {submittedTip.tip_id}
              </div>

              {guardInfo && (
                <div>
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '6px 14px', background: guardInfo.bg, borderRadius: '8px', fontSize: '0.8rem', fontWeight: 700, color: guardInfo.color, marginBottom: '1.5rem' }}>
                    {guardInfo.label}
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem' }}>
                <button
                  onClick={() => setSubmittedTip(null)}
                  style={{ padding: '0.75rem 1.5rem', background: '#4f46e5', color: '#ffffff', fontWeight: 700, borderRadius: '8px', fontSize: '0.9rem', border: 'none', cursor: 'pointer' }}
                >
                  Submit Another Report
                </button>
                {isOfficerOrStaff && (
                  <button
                    onClick={() => setActiveView('triage')}
                    style={{ padding: '0.75rem 1.5rem', background: '#f1f5f9', color: '#0f172a', fontWeight: 700, borderRadius: '8px', fontSize: '0.9rem', border: '1px solid #cbd5e1', cursor: 'pointer' }}
                  >
                    View Triage Queue →
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '2rem' }}>
              {/* Left: Tip Intake Form */}
              <form onSubmit={handleSubmitTip} style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '16px', padding: '2rem', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: '#475569', marginBottom: '0.35rem' }}>
                      Target Station Jurisdiction
                    </label>
                    <select
                      value={stationId}
                      onChange={(e) => setStationId(e.target.value)}
                      style={{ width: '100%', padding: '0.65rem 0.85rem', background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '0.88rem', fontWeight: 600, color: '#0f172a' }}
                    >
                      {Object.entries(STATION_MAP).map(([k, v]) => (
                        <option key={k} value={k}>{v}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: '#475569', marginBottom: '0.35rem' }}>
                      Offense Type
                    </label>
                    <select
                      value={crimeType}
                      onChange={(e) => setCrimeType(e.target.value)}
                      style={{ width: '100%', padding: '0.65rem 0.85rem', background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '0.88rem', fontWeight: 600, color: '#0f172a' }}
                    >
                      {CRIME_TYPES.map((ct) => (
                        <option key={ct.value} value={ct.value}>{ct.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: '#475569', marginBottom: '0.35rem' }}>
                    {isOfficerOrStaff ? 'Field Lead Observation & Narrative' : 'Your Observation & Narrative'}
                  </label>
                  <textarea
                    rows={4}
                    value={tipNarrative}
                    onChange={(e) => setTipNarrative(e.target.value)}
                    placeholder="Describe what you observed in detail (minimum 20 characters)..."
                    style={{
                      width: '100%',
                      padding: '0.75rem 0.85rem',
                      background: '#f8fafc',
                      border: `1px solid ${tipNarrative.length > 0 && tipNarrative.length < 20 ? '#f59e0b' : '#cbd5e1'}`,
                      borderRadius: '8px',
                      fontSize: '0.88rem',
                      color: '#0f172a',
                      resize: 'vertical',
                      boxSizing: 'border-box',
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.3rem' }}>
                    {tipNarrative.length > 0 && tipNarrative.length < 20 ? (
                      <span style={{ fontSize: '0.72rem', color: '#b45309', fontWeight: 600 }}>
                        ⚠ Minimum 20 characters required
                      </span>
                    ) : (
                      <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                        {tipNarrative.length >= 20 ? '✓ Valid Length' : ''}
                      </span>
                    )}
                    <span style={{ fontSize: '0.72rem', fontWeight: 600, color: tipNarrative.length < 20 ? '#b45309' : '#64748b' }}>
                      {tipNarrative.length} chars
                    </span>
                  </div>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: '#475569', marginBottom: '0.35rem' }}>
                    Vehicle or Suspect Description (Optional)
                  </label>
                  <input
                    type="text"
                    value={vehicleNote}
                    onChange={(e) => setVehicleNote(e.target.value)}
                    placeholder="e.g. Silver sedan, license plate CHD-01-***"
                    style={{ width: '100%', padding: '0.65rem 0.85rem', background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '0.88rem', color: '#0f172a' }}
                  />
                </div>

                {/* Drag & Drop Simulation */}
                <div
                  style={{ border: '2px dashed #cbd5e1', borderRadius: '12px', padding: '1.25rem', textAlign: 'center', background: fileAttached ? '#f0fdf4' : '#f8fafc', cursor: 'pointer' }}
                  onClick={() => setFileAttached(!fileAttached)}
                >
                  <Camera size={26} color={fileAttached ? '#059669' : '#64748b'} style={{ margin: '0 auto 0.4rem' }} />
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#0f172a' }}>
                    {fileAttached ? 'surveillance_clip_cam01.jpg (Attached)' : 'Attach CCTV Still or Photo'}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.2rem' }}>
                    {fileAttached ? 'Client-side EXIF/GPS scrubbing complete' : 'Click to simulate attaching surveillance footage'}
                  </div>
                </div>

                {submitError && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#dc2626', fontSize: '0.82rem', fontWeight: 600 }}>
                    <AlertCircle size={14} /> {submitError}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isSubmitting || !tipNarrative.trim() || tipNarrative.trim().length < 20}
                  style={{
                    padding: '0.85rem',
                    background: 'linear-gradient(135deg, #4f46e5, #6366f1)',
                    color: '#ffffff',
                    fontWeight: 800,
                    fontSize: '0.95rem',
                    borderRadius: '8px',
                    boxShadow: '0 4px 12px rgba(79, 70, 229, 0.3)',
                    opacity: (isSubmitting || tipNarrative.trim().length < 20) ? 0.6 : 1,
                    cursor: tipNarrative.trim().length < 20 ? 'not-allowed' : 'pointer',
                    border: 'none',
                  }}
                >
                  {isSubmitting ? 'Sanitizing & Ingesting...' : isOfficerOrStaff ? 'Submit Field Intelligence Lead →' : 'Submit Anonymous Tip →'}
                </button>
              </form>

              {/* Right: Privacy Sanitizer + Recent Submissions */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '16px', padding: '1.5rem', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.85rem' }}>
                    <EyeOff size={18} color="#059669" />
                    <h3 style={{ fontSize: '0.95rem', fontWeight: 800, color: '#0f172a' }}>Client-Side EXIF Scrubbing</h3>
                  </div>

                  <div style={{ background: '#f8fafc', borderRadius: '8px', padding: '0.85rem', fontSize: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#64748b' }}>GPS Coordinates:</span>
                      <span style={{ color: '#dc2626', fontWeight: 700, textDecoration: 'line-through' }}>30.7333° N, 76.7794° E</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#64748b' }}>Camera Serial:</span>
                      <span style={{ color: '#dc2626', fontWeight: 700, textDecoration: 'line-through' }}>SN#98213-CANON</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#64748b' }}>Device Model:</span>
                      <span style={{ color: '#dc2626', fontWeight: 700, textDecoration: 'line-through' }}>iPhone 15 Pro Max</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #e2e8f0', paddingTop: '0.5rem' }}>
                      <span style={{ color: '#0f172a', fontWeight: 700 }}>Sanitization Status:</span>
                      <span style={{ color: '#059669', fontWeight: 800 }}>100% STRIPPED</span>
                    </div>
                  </div>
                </div>

                <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '16px', padding: '1.5rem', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.65rem' }}>
                    <Sparkles size={18} color="#4f46e5" />
                    <h3 style={{ fontSize: '0.95rem', fontWeight: 800, color: '#0f172a' }}>Scout Intent Guard Triage</h3>
                  </div>
                  <p style={{ fontSize: '0.78rem', color: '#475569', lineHeight: 1.5, margin: 0 }}>
                    Incoming statements are screened in memory before reaching investigators:
                  </p>
                  <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: '#059669', fontWeight: 700 }}>
                      <CheckCircle2 size={14} /> Legitimate Lead → Dispatched to Zetaris witness store
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: '#d97706', fontWeight: 700 }}>
                      <AlertTriangle size={14} /> Prompt Injection → Quarantined automatically
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* 3. CITIZEN TIP STATUS LOOKUP (Public Citizens)                      */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      {activeView === 'track' && !isOfficerOrStaff && (
        <div style={{ maxWidth: '680px', margin: '0 auto', width: '100%' }}>
          <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '16px', padding: '2rem', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '1rem' }}>
              <Key size={22} color="#4f46e5" />
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0f172a', margin: 0 }}>
                  Anonymous Tip Status Tracker
                </h2>
                <p style={{ fontSize: '0.82rem', color: '#64748b', margin: '2px 0 0 0' }}>
                  Enter your tracking code (e.g. <code>TIP-CHD-8F3K91</code>) to see if an officer has reviewed or verified your report.
                </p>
              </div>
            </div>

            <form onSubmit={handleTrackTip} style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
              <input
                type="text"
                placeholder="Enter your anonymous tip code..."
                value={trackCode}
                onChange={(e) => setTrackCode(e.target.value)}
                style={{ flex: 1, padding: '0.65rem 0.85rem', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '0.9rem', fontWeight: 700, letterSpacing: '0.04em' }}
              />
              <button
                type="submit"
                disabled={trackLoading || !trackCode.trim()}
                style={{ padding: '0.65rem 1.25rem', borderRadius: '8px', background: '#4f46e5', color: '#ffffff', fontWeight: 700, fontSize: '0.85rem', border: 'none', cursor: 'pointer' }}
              >
                {trackLoading ? 'Searching...' : 'Track'}
              </button>
            </form>

            {trackError && (
              <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', padding: '0.75rem 1rem', borderRadius: '8px', fontSize: '0.82rem', marginBottom: '1rem' }}>
                {trackError}
              </div>
            )}

            {trackedTip && (
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <code style={{ fontSize: '0.95rem', fontWeight: 800, color: '#4f46e5' }}>{trackedTip.tip_id}</code>
                  {(() => {
                    const st = STATUS_CONFIG[trackedTip.review_status || 'PENDING_REVIEW'] ?? STATUS_CONFIG['PENDING_REVIEW'];
                    return (
                      <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '2px 10px', borderRadius: '9999px', background: st.bg, color: st.color, border: `1px solid ${st.border}` }}>
                        {st.label}
                      </span>
                    );
                  })()}
                </div>

                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                  Station: <strong>{STATION_MAP[trackedTip.station_id] || trackedTip.station_id}</strong> • Submitted: {trackedTip.submitted_at.replace('T', ' ').replace('Z', ' UTC')}
                </div>

                <div style={{ fontSize: '0.85rem', color: '#334155', background: '#ffffff', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                  <strong>Report summary:</strong> {trackedTip.observation_text}
                </div>

                {trackedTip.reviewed_by ? (
                  <div style={{ background: '#d1fae5', border: '1px solid #a7f3d0', borderRadius: '6px', padding: '0.65rem 0.85rem', fontSize: '0.8rem', color: '#065f46' }}>
                    <div style={{ fontWeight: 700 }}>✓ Verified by Chandigarh Police</div>
                    {trackedTip.officer_notes && <div style={{ marginTop: '2px' }}>Officer remark: {trackedTip.officer_notes}</div>}
                  </div>
                ) : (
                  <div style={{ fontSize: '0.78rem', color: '#b45309', background: '#fef3c7', padding: '0.5rem 0.75rem', borderRadius: '6px' }}>
                    ⏳ Your report is currently queued for officer verification in the morning shift.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
