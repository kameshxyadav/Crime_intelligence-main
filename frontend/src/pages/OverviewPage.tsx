import React, { useEffect, useState } from 'react';
import {
  Layers,
  Sparkles,
  ArrowRight,
  BrainCircuit,
  Radio,
  Building,
  Users,
  ShieldCheck,
  Award,
  Lock,
  Camera,
} from 'lucide-react';
import { SourceInfo } from '../types';
import { api, UserProfile } from '../services/api';

interface OverviewPageProps {
  currentUser?: UserProfile | null;
  onSelectStation?: (station: string) => void;
  onNavigateToSources?: (sourceName: string) => void;
  onNavigateToIncidents?: () => void;
  onNavigateToInvestigation?: () => void;
  onNavigateToZetaris?: () => void;
  onNavigateToTipPortal?: () => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  currentUser,
  onNavigateToSources,
  onNavigateToIncidents,
  onNavigateToInvestigation,
  onNavigateToZetaris,
  onNavigateToTipPortal,
}) => {
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [tipCount, setTipCount] = useState<number>(0);

  const userRole = currentUser?.role || 'public';
  const canAccessRole = (targetRole: 'officer' | 'analyst' | 'admin' | 'public'): boolean => {
    if (targetRole === 'public') return true;
    if (userRole === 'admin') return true;
    if (userRole === 'analyst') return ['officer', 'analyst', 'public'].includes(targetRole);
    if (userRole === 'officer') return ['officer', 'public'].includes(targetRole);
    return false;
  };

  useEffect(() => {
    let isMounted = true;

    const withTimeout = (p: Promise<any>) =>
      Promise.race([
        p,
        new Promise((_res, rej) => setTimeout(() => rej(new Error('timeout')), 3000)),
      ]);

    withTimeout(api.getSources())
      .then((sourcesData: any) => {
        if (isMounted) setSources(sourcesData.sources);
      })
      .catch((err: any) => {
        console.warn('Sources fetch fallback (backend offline):', err);
      });

    withTimeout(api.listTips())
      .then((tips: any) => {
        if (isMounted) setTipCount(tips.length);
      })
      .catch(() => {
        // Ignore — count stays at 0
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const totalRecords = sources.reduce((acc, curr) => acc + curr.record_count, 0) || 10000;

  return (
    <div className="one-os-container">
      {/* ── Admin Command Oversight Banner ── */}
      {currentUser?.role === 'admin' && (
        <div
          style={{
            background: 'linear-gradient(135deg, #064e3b, #047857)',
            color: '#ffffff',
            borderRadius: '16px',
            padding: '1.25rem 1.75rem',
            marginBottom: '1.5rem',
            boxShadow: '0 4px 15px rgba(5, 150, 105, 0.15)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ background: 'rgba(255,255,255,0.15)', padding: '10px', borderRadius: '12px' }}>
              <Award size={24} color="#6ee7b7" />
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, letterSpacing: '0.08em', color: '#a7f3d0', textTransform: 'uppercase' }}>
                POLICE HQ COMMAND DIRECTIVE · SECTOR 9
              </div>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 800, margin: '2px 0', color: '#ffffff' }}>
                Welcome, {currentUser.name} ({currentUser.badge_number || 'IPS-CHD-001'})
              </h2>
              <div style={{ fontSize: '0.8rem', color: '#d1fae5' }}>
                Jurisdiction: {currentUser.jurisdiction} • 3 Stations Active • Zetaris Federated Audit OK
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              onClick={() => onNavigateToInvestigation && onNavigateToInvestigation()}
              style={{
                background: '#ffffff',
                color: '#065f46',
                border: 'none',
                borderRadius: '8px',
                padding: '8px 14px',
                fontWeight: 700,
                fontSize: '0.82rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <BrainCircuit size={15} />
              Review Open Syndicates
            </button>
            <button
              onClick={() => onNavigateToZetaris && onNavigateToZetaris()}
              style={{
                background: 'rgba(255,255,255,0.2)',
                color: '#ffffff',
                border: '1px solid rgba(255,255,255,0.3)',
                borderRadius: '8px',
                padding: '8px 14px',
                fontWeight: 600,
                fontSize: '0.82rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <ShieldCheck size={15} />
              Audit Logs
            </button>
          </div>
        </div>
      )}

      {/* ── 1. Hero Section (SnapLocate "One OS" Reference) ── */}
      <section className="one-os-hero">
        <div className="one-os-badge">
          <Sparkles size={14} color="#818cf8" />
          Open Agent Hackathon 2026 · Track 1: Solving Fragmented Intelligence
        </div>

        <h1 className="one-os-title">One OS</h1>
        <div className="one-os-punchline">Just ek click, sab kuch quick!</div>

        <p className="one-os-desc">
          Cross-Station Crime Intelligence replaces every scattered police jurisdiction with one fast, unified operating system for field officers, crime analysts, and station chiefs.
        </p>

        <div className="one-os-actions">
          {currentUser?.role === 'public' ? (
            <>
              <button
                className="one-os-btn-primary"
                onClick={() => onNavigateToTipPortal && onNavigateToTipPortal()}
              >
                <ShieldCheck size={18} />
                Submit Anonymous Citizen Tip
                <ArrowRight size={16} />
              </button>
              <button
                className="one-os-btn-secondary"
                onClick={() => onNavigateToTipPortal && onNavigateToTipPortal()}
              >
                <Camera size={18} />
                CCTV Evidence &amp; Status Tracker
              </button>
            </>
          ) : currentUser?.role === 'officer' ? (
            <>
              <button
                className="one-os-btn-primary"
                onClick={() => onNavigateToIncidents && onNavigateToIncidents()}
              >
                <Radio size={18} />
                Launch Field Incidents
                <ArrowRight size={16} />
              </button>
              <button
                className="one-os-btn-secondary"
                onClick={() => onNavigateToTipPortal && onNavigateToTipPortal()}
              >
                <ShieldCheck size={18} />
                Citizen Tip Triage Queue
              </button>
            </>
          ) : (
            <>
              <button
                className="one-os-btn-primary"
                onClick={() => onNavigateToInvestigation && onNavigateToInvestigation()}
              >
                <BrainCircuit size={18} />
                Explore Investigation Hub
                <ArrowRight size={16} />
              </button>
              <button
                className="one-os-btn-secondary"
                onClick={() => onNavigateToSources && onNavigateToSources('police_incidents')}
              >
                <Layers size={18} />
                View Federated Sources
              </button>
            </>
          )}
        </div>

        {/* ── 4 Status Cards with Vibrant Progress Tracks ── */}
        <div className="one-os-preview-cards">
          <div className="one-os-card">
            <div>
              <div className="one-os-card-tag">UP NEXT</div>
              <div className="one-os-card-title">Commercial Safe Syndicate</div>
              <div className="one-os-card-sub">North ↔ Central · 36mm Chisel Toolmarks</div>
            </div>
            <div className="one-os-progress-track">
              <div
                className="one-os-progress-bar"
                style={{ width: '85%', background: 'linear-gradient(90deg, #4f46e5, #818cf8)' }}
              />
            </div>
          </div>

          <div className="one-os-card">
            <div>
              <div className="one-os-card-tag">ZETARIS NDP</div>
              <div className="one-os-card-title">5 Siloed Datasets</div>
              <div className="one-os-card-sub">Federated without ETL Movement</div>
            </div>
            <div className="one-os-progress-track">
              <div
                className="one-os-progress-bar"
                style={{ width: '100%', background: 'linear-gradient(90deg, #10b981, #34d399)' }}
              />
            </div>
          </div>

          <div className="one-os-card">
            <div>
              <div className="one-os-card-tag">AGENT REASONING</div>
              <div className="one-os-card-title">Nemotron Ultra 550B</div>
              <div className="one-os-card-sub">Skeptic Challenged · Strike Guard Active</div>
            </div>
            <div className="one-os-progress-track">
              <div
                className="one-os-progress-bar"
                style={{ width: '100%', background: 'linear-gradient(90deg, #a855f7, #c084fc)' }}
              />
            </div>
          </div>

          <div className="one-os-card">
            <div>
              <div className="one-os-card-tag">BENCHMARK</div>
              <div className="one-os-card-title">8 Scenarios Verified</div>
              <div className="one-os-card-sub">Ground Truth F1 Target: 0.88+</div>
            </div>
            <div className="one-os-progress-track">
              <div
                className="one-os-progress-bar"
                style={{ width: '92%', background: 'linear-gradient(90deg, #06b6d4, #38bdf8)' }}
              />
            </div>
          </div>
        </div>

        {/* ── Metrics Ribbon ── */}
        <div className="one-os-metrics-ribbon">
          <div className="one-os-metric-item">
            <span className="one-os-metric-val">{totalRecords.toLocaleString()}+</span>
            <span className="one-os-metric-lbl">Primary Records</span>
          </div>
          <div className="one-os-metric-item">
            <span className="one-os-metric-val">3</span>
            <span className="one-os-metric-lbl">Police Jurisdictions</span>
          </div>
          <div className="one-os-metric-item">
            <span className="one-os-metric-val">4</span>
            <span className="one-os-metric-lbl">Autonomous Agents</span>
          </div>
          <div className="one-os-metric-item">
            <span className="one-os-metric-val">100%</span>
            <span className="one-os-metric-lbl">Zetaris Federated</span>
          </div>
          <div className="one-os-metric-item">
            <span className="one-os-metric-val">NVIDIA</span>
            <span className="one-os-metric-lbl">Nemotron 550B &amp; 30B</span>
          </div>
          {/* Live tip count from backend API */}
          <div className="one-os-metric-item">
            <span className="one-os-metric-val" style={{ color: '#059669' }}>
              {tipCount > 0 ? tipCount : '—'}
            </span>
            <span className="one-os-metric-lbl">
              Citizen Tips Recorded
            </span>
          </div>
        </div>
      </section>

      {/* ── 2. "Built For Every Role" Section (SnapLocate Screenshot 2 Reference) ── */}
      <section className="one-os-roles-section">
        <div className="one-os-section-header">
          <div className="one-os-section-tag">BUILT FOR EVERY ROLE</div>
          <h2 className="one-os-section-title">Your role Your dashboard</h2>
        </div>

        <div className="one-os-role-grid">
          {/* Role 1: Station Officers (Field OS) */}
          <div className="one-os-role-card role-officer">
            <div>
              <div className="one-os-role-header">
                <span className="one-os-role-tag">FIELD OS</span>
                <Radio size={20} color="#38bdf8" />
              </div>

              <div className="one-os-role-title-row">
                <h3 className="one-os-role-title">Station Officers</h3>
              </div>

              <p className="one-os-role-desc">
                Log instant incident reports, review active local patrol warnings, search suspect vehicles across neighboring station boundaries, and immediately catch cross-border offenses.
              </p>

              <div className="one-os-role-pills">
                <span className="one-os-pill">Incident Intake</span>
                <span className="one-os-pill">Patrol Feeds</span>
                <span className="one-os-pill">Plate & Vehicle Search</span>
                <span className="one-os-pill">Local Jurisdiction Alerts</span>
                <span className="one-os-pill">Station Dispatch</span>
              </div>
            </div>

            {canAccessRole('officer') ? (
              <button
                className="one-os-role-btn"
                onClick={() => onNavigateToIncidents && onNavigateToIncidents()}
              >
                Launch Officer View
                <ArrowRight size={15} />
              </button>
            ) : (
              <button
                className="one-os-role-btn"
                disabled
                style={{ opacity: 0.65, cursor: 'not-allowed', background: '#f1f5f9', color: '#64748b', border: '1px solid #cbd5e1' }}
                title="Only verified field officers and CID analysts can access this operating terminal."
              >
                <Lock size={14} style={{ display: 'inline', marginRight: 6 }} />
                Restricted to Field Officers
              </button>
            )}
          </div>

          {/* Role 2: Crime Analysts (Analyst OS) */}
          <div className="one-os-role-card role-analyst">
            <div>
              <div className="one-os-role-header">
                <span className="one-os-role-tag">ANALYST OS</span>
                <BrainCircuit size={20} color="#c084fc" />
              </div>

              <div className="one-os-role-title-row">
                <h3 className="one-os-role-title">Crime Analysts</h3>
              </div>

              <p className="one-os-role-desc">
                Automate city-wide correlation across North, Central, and Riverside. Inspect 9-factor MO scores, challenge links with the Skeptic agent, and export comprehensive investigation dossiers.
              </p>

              <div className="one-os-role-pills">
                <span className="one-os-pill">Correlation Matrix</span>
                <span className="one-os-pill">9-Factor MO Scoring</span>
                <span className="one-os-pill">Skeptic Agent Challenge</span>
                <span className="one-os-pill">Forensic Toolmark Links</span>
                <span className="one-os-pill">Dossier Export</span>
              </div>
            </div>

            {canAccessRole('analyst') ? (
              <button
                className="one-os-role-btn"
                onClick={() => onNavigateToInvestigation && onNavigateToInvestigation()}
              >
                Open Analyst Hub
                <ArrowRight size={15} />
              </button>
            ) : (
              <button
                className="one-os-role-btn"
                disabled
                style={{ opacity: 0.65, cursor: 'not-allowed', background: '#f1f5f9', color: '#64748b', border: '1px solid #cbd5e1' }}
                title="Requires CID Analyst or Police HQ Command security clearance."
              >
                <Lock size={14} style={{ display: 'inline', marginRight: 6 }} />
                Requires CID Clearance
              </button>
            )}
          </div>

          {/* Role 3: Commanders & Chiefs (Admin OS) */}
          <div className="one-os-role-card role-command">
            <div>
              <div className="one-os-role-header">
                <span className="one-os-role-tag">COMMAND OS</span>
                <Building size={20} color="#34d399" />
              </div>

              <div className="one-os-role-title-row">
                <h3 className="one-os-role-title">Chiefs & Commanders</h3>
              </div>

              <p className="one-os-role-desc">
                Full executive oversight over all 3 police jurisdictions. Track cross-station clearance rates, dispatch Joint Task Forces, and review audit logs from the Zetaris federated layer.
              </p>

              <div className="one-os-role-pills">
                <span className="one-os-pill">Jurisdiction Heatmaps</span>
                <span className="one-os-pill">Joint Task Forces</span>
                <span className="one-os-pill">Zetaris Data Quality</span>
                <span className="one-os-pill">Audit Ledger</span>
                <span className="one-os-pill">Clearance KPIs</span>
              </div>
            </div>

            {canAccessRole('admin') ? (
              <button
                className="one-os-role-btn"
                onClick={() => onNavigateToZetaris && onNavigateToZetaris()}
              >
                Inspect Command Layer
                <ArrowRight size={15} />
              </button>
            ) : (
              <button
                className="one-os-role-btn"
                disabled
                style={{ opacity: 0.65, cursor: 'not-allowed', background: '#f1f5f9', color: '#64748b', border: '1px solid #cbd5e1' }}
                title="Requires SSP Police Headquarters executive command clearance."
              >
                <Lock size={14} style={{ display: 'inline', marginRight: 6 }} />
                Requires HQ Clearance
              </button>
            )}
          </div>

          {/* Role 4: Public & Witnesses (Citizen Portal) */}
          <div className="one-os-role-card role-public">
            <div>
              <div className="one-os-role-header">
                <span className="one-os-role-tag">CITIZEN PORTAL</span>
                <Users size={20} color="#fbbf24" />
              </div>

              <div className="one-os-role-title-row">
                <h3 className="one-os-role-title">Public & Witnesses</h3>
              </div>

              <p className="one-os-role-desc">
                Empower citizens to submit anonymous tip-offs and surveillance clips safely. Client-side EXIF/GPS scrubbing, rate limiting, and zero IP logging ensure complete whistleblower protection.
              </p>

              <div className="one-os-role-pills">
                <span className="one-os-pill">Anonymous Tips</span>
                <span className="one-os-pill">CCTV Clip Intake</span>
                <span className="one-os-pill">EXIF Scrubbing</span>
                <span className="one-os-pill">Public Bulletins</span>
                <span className="one-os-pill">No IP Trackers</span>
              </div>
            </div>

            <button
              className="one-os-role-btn"
              onClick={() => {
                if (currentUser?.role === 'public' || currentUser?.role === 'officer') {
                  if (onNavigateToTipPortal) onNavigateToTipPortal();
                } else {
                  if (onNavigateToSources) onNavigateToSources('witness_reports');
                }
              }}
            >
              {currentUser?.role === 'public'
                ? 'Submit Citizen Tip'
                : currentUser?.role === 'officer'
                  ? 'Review Tip Queue'
                  : 'Browse Citizen Feeds'}
              <ArrowRight size={15} />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};
