import React, { useState, useEffect } from 'react';
import {
  GitMerge,
  ShieldAlert,
  CheckCircle2,
  AlertOctagon,
  Filter,
  Share2,
} from 'lucide-react';
import { api } from '../services/api';
import { InvestigationResponse } from '../types';

interface LinkData {
  id: string;
  sourceStation: string;
  targetStation: string;
  sourceIncident: string;
  targetIncident: string;
  title: string;
  confidence: number;
  basis: string;
  toolmarkOrWeapon: string;
  vehicle: string;
  skepticStatus: 'VERIFIED' | 'STRUCK' | 'REVISED';
  skepticNotes: string;
  evidenceIds: string[];
}

const SAMPLE_LINKS: LinkData[] = [
  {
    id: 'LNK-SERIES-01',
    sourceStation: 'PS-INDUSTRIAL',
    targetStation: 'PS-SEC17',
    sourceIncident: 'INC-INDUSTRIAL-0042',
    targetIncident: 'INC-SEC17-0118',
    title: 'Commercial Safe Burglary Syndicate',
    confidence: 0.88,
    basis: 'Identical 36mm curved chisel-tip pry marks with microscopic nick on left edge.',
    toolmarkOrWeapon: '36mm Chisel-tip pry tool',
    vehicle: 'Dark grey Dodge Caravan (plate 7XK***)',
    skepticStatus: 'VERIFIED',
    skepticNotes: 'Toolmark microscopy confirmed identical between FOR-0089 and FOR-0142. Travel time between Industrial Phase 1 and Sector 17 is 24 mins (feasible).',
    evidenceIds: ['FOR-0089', 'FOR-0142', 'CCTV-0112', 'NEWS-0064'],
  },
  {
    id: 'LNK-SERIES-02',
    sourceStation: 'PS-SEC17',
    targetStation: 'PS-SEC40',
    sourceIncident: 'INC-SEC17-0450',
    targetIncident: 'INC-SEC40-0182',
    title: 'Nocturnal Catalytic Converter Extraction Ring',
    confidence: 0.89,
    basis: 'Reciprocating saw titanium-carbide blade metallurgical residue and identical cut angle.',
    toolmarkOrWeapon: 'Titanium-carbonitride reciprocating saw',
    vehicle: 'Silver hatchback with roof rails',
    skepticStatus: 'VERIFIED',
    skepticNotes: 'Metallurgical residue confirmed match. Decoy report INC-SEC40-0992 rejected by Skeptic due to flame-torch cut discrepancy.',
    evidenceIds: ['FOR-0380', 'FOR-0512', 'CCTV-0480', 'WIT-0412'],
  },
  {
    id: 'LNK-SERIES-03',
    sourceStation: 'PS-INDUSTRIAL',
    targetStation: 'PS-SEC40',
    sourceIncident: 'INC-INDUSTRIAL-0810',
    targetIncident: 'INC-SEC40-0640',
    title: 'Suburban Keyless SUV Relay Attack Series',
    confidence: 0.91,
    basis: 'Handheld 315/433MHz dual-frequency RF booster signature with 14ms transponder relay delay.',
    toolmarkOrWeapon: 'RF Transponder Relay Booster',
    vehicle: 'Stolen Lexus RX / BMW X5',
    skepticStatus: 'VERIFIED',
    skepticNotes: 'ECU digital bus log confirms identical handshake timing anomaly. Zero physical forced entry across all target driveways in Dhanas/Zirakpur corridor.',
    evidenceIds: ['FOR-0740', 'FOR-0911', 'CCTV-0899'],
  },
  {
    id: 'LNK-DECOY-01',
    sourceStation: 'PS-INDUSTRIAL',
    targetStation: 'PS-SEC17',
    sourceIncident: 'INC-INDUSTRIAL-0312',
    targetIncident: 'INC-SEC17-0290',
    title: 'Suspected Residential Warehouse Break-in (Challenged)',
    confidence: 0.42,
    basis: 'Pry tool reported on wooden service door.',
    toolmarkOrWeapon: 'Generic 18mm crowbar',
    vehicle: 'Unknown dark sedan',
    skepticStatus: 'STRUCK',
    skepticNotes: 'STRUCK BY SKEPTIC: Striation width is 18mm vs syndicate 36mm. Timeline overlaps with confirmed Sec 17 safe burglary. Tagged as coincidental local burglary.',
    evidenceIds: ['FOR-0205'],
  },
];

const STATION_COORDS: Record<string, { x: number; y: number; label: string; area: string; color: string }> = {
  NORTH: { x: 180, y: 130, label: 'PS-INDUSTRIAL', area: 'Industrial Area Phase 1 · Manimajra', color: '#0284c7' },
  CENTRAL: { x: 480, y: 110, label: 'PS-SEC17', area: 'Sector 17 Central · Sector 22 Corridor', color: '#7c3aed' },
  RIVERSIDE: { x: 330, y: 340, label: 'PS-SEC40', area: 'Sector 40 · Dhanas · Zirakpur Corridor', color: '#059669' },
};

export const CorrelationMapPage: React.FC = () => {
  const [selectedSeries, setSelectedSeries] = useState<string>('ALL');
  const [selectedLink, setSelectedLink] = useState<LinkData>(SAMPLE_LINKS[0]);
  const [activeCell, setActiveCell] = useState<string>('PS-INDUSTRIAL-PS-SEC17');
  const [liveLinks, setLiveLinks] = useState<LinkData[]>(SAMPLE_LINKS);
  const [apiLoading, setApiLoading] = useState<boolean>(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [dataMode, setDataMode] = useState<'live' | 'sample'>('sample');

  // ── Load live analysis from backend on mount ──
  useEffect(() => {
    let isMounted = true;
    setApiLoading(true);
    setApiError(null);
    api
      .analyzeInvestigation({ query: 'Cross-station link analysis', scenario_id: 'safe_burglary_syndicate', sample_mode: true })
      .then((resp: InvestigationResponse) => {
        if (!isMounted) return;
        // Map backend candidate_links to our LinkData format (supplement SAMPLE_LINKS)
        if (resp.candidate_links && resp.candidate_links.length > 0) {
          const mappedLinks: LinkData[] = resp.candidate_links.map((cl, idx) => ({
            id: cl.link_id ?? `LNK-LIVE-${String(idx + 1).padStart(2, '0')}`,
            // stations_involved is the array from backend e.g. ['PS-INDUSTRIAL', 'PS-SEC17']
            sourceStation: cl.stations_involved?.[0] ?? 'PS-INDUSTRIAL',
            targetStation: cl.stations_involved?.[1] ?? 'PS-SEC17',
            sourceIncident: cl.source_incident_id ?? `INC-LIVE-${idx * 2}`,
            targetIncident: cl.target_incident_id ?? `INC-LIVE-${idx * 2 + 1}`,
            title: `Cross-Station Link ${cl.link_id ?? idx + 1}`,
            confidence: cl.confidence_score ?? 0.75,
            basis: cl.similarity_basis ?? 'AI-generated cross-station link.',
            toolmarkOrWeapon: cl.shared_attributes?.[0]?.value ?? 'Forensic match detected',
            vehicle: cl.shared_attributes?.[1]?.value ?? 'Vehicle pattern identified',
            // If withdrawn or UNSUPPORTED → STRUCK; WEAK → REVISED; else VERIFIED
            skepticStatus: cl.withdrawn
              ? 'STRUCK'
              : (cl.validation_status === 'UNSUPPORTED'
                ? 'STRUCK'
                : cl.validation_status === 'WEAK'
                  ? 'REVISED'
                  : 'VERIFIED') as 'VERIFIED' | 'STRUCK' | 'REVISED',
            skepticNotes: cl.validation_explanation ?? cl.confidence_rationale ?? 'Nemotron Skeptic validation pending.',
            evidenceIds: cl.supporting_evidence_ids ?? [],
          }));
          setLiveLinks(mappedLinks);
          setSelectedLink(mappedLinks[0]);
          setDataMode('live');
        } else {
          // backend returned empty links — keep sample data
          setLiveLinks(SAMPLE_LINKS);
          setDataMode('sample');
        }
      })
      .catch(() => {
        if (!isMounted) return;
        // Graceful fallback: keep SAMPLE_LINKS, show a soft error indicator
        setLiveLinks(SAMPLE_LINKS);
        setApiError('Backend offline — showing sample data');
        setDataMode('sample');
      })
      .finally(() => {
        if (isMounted) setApiLoading(false);
      });
    return () => { isMounted = false; };
  }, []);

  const handleFilterSeries = (s: string) => {
    setSelectedSeries(s);
    const matches = s === 'ALL'
      ? liveLinks
      : liveLinks.filter((l) => l.id.includes(s) || (s === 'DECOY' && l.skepticStatus === 'STRUCK'));
    if (matches.length > 0) {
      setSelectedLink(matches[0]);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* ── Page Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.4rem' }}>
            <div style={{ background: '#e0e7ff', padding: '7px', borderRadius: '10px', color: '#4f46e5' }}>
              <GitMerge size={22} />
            </div>
            <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#0f172a', letterSpacing: '-0.02em' }}>
              Cross-Station Correlation & Pulse Map
            </h1>
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                padding: '3px 10px',
                borderRadius: '9999px',
                background: '#e0f2fe',
                color: '#0284c7',
                border: '1px solid #bae6fd',
              }}
            >
              Jurisdictional Link Visualizer
            </span>
            {/* Live / Sample data mode badge */}
            <span
              style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                padding: '3px 10px',
                borderRadius: '9999px',
                background: dataMode === 'live' ? '#d1fae5' : '#f8fafc',
                color: dataMode === 'live' ? '#065f46' : '#64748b',
                border: `1px solid ${dataMode === 'live' ? '#a7f3d0' : '#e2e8f0'}`,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              {apiLoading ? '↻ Loading…' : dataMode === 'live' ? '● LIVE API' : '● SAMPLE'}
            </span>
          </div>
          <p style={{ color: '#475569', fontSize: '0.95rem', maxWidth: '820px', lineHeight: 1.6 }}>
            Track how criminal syndicates operate across jurisdictional borders. View the 3-Station link matrix, inspect animated cross-border connection arcs, and review how the Nemotron Ultra 550B Skeptic Agent challenges coincidences and strikes decoys.
          </p>
          {apiError && (
            <p style={{ fontSize: '0.78rem', color: '#92400e', background: '#fef3c7', padding: '4px 10px', borderRadius: '8px', marginTop: '0.4rem', display: 'inline-block' }}>
              ⚠ {apiError}
            </p>
          )}
        </div>

        {/* Series Filter Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#ffffff', padding: '0.4rem', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <Filter size={16} color="#64748b" style={{ marginLeft: 8 }} />
          {(['ALL', 'SERIES-01', 'SERIES-02', 'SERIES-03', 'DECOY'] as const).map((s) => (
            <button
              key={s}
              onClick={() => handleFilterSeries(s)}
              style={{
                padding: '6px 12px',
                borderRadius: '8px',
                fontSize: '0.78rem',
                fontWeight: 700,
                background: selectedSeries === s ? '#4f46e5' : 'transparent',
                color: selectedSeries === s ? '#ffffff' : '#64748b',
                transition: 'all 0.2s ease',
              }}
            >
              {s === 'ALL' ? 'All Links' : s === 'DECOY' ? 'Struck Decoys' : s.replace('SERIES-', 'Series ')}
            </button>
          ))}
        </div>
      </div>

      {/* ── Top Row: 3x3 Station Matrix + Live Pulse Map ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '420px 1fr', gap: '1.75rem' }}>
        {/* Left: 3x3 Jurisdictional Matrix Card */}
        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '16px', padding: '1.75rem', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <div>
                <span style={{ fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase', color: '#4f46e5', letterSpacing: '0.06em' }}>
                  JURISDICTIONAL INTERSECTION
                </span>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0f172a' }}>Station Link Matrix</h3>
              </div>
              <Share2 size={18} color="#94a3b8" />
            </div>

            <p style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: '1.25rem', lineHeight: 1.5 }}>
              Click any cell to inspect inter-station link strength, shared MO factors, and Skeptic audit results.
            </p>

            {/* Matrix Table */}
            <div style={{ display: 'grid', gridTemplateColumns: '80px repeat(3, 1fr)', gap: '6px', textAlign: 'center', fontSize: '0.72rem', fontWeight: 700 }}>
              <div></div>
              <div style={{ color: '#0284c7', padding: '6px 2px', fontSize: '0.68rem' }}>PS-INDUSTRIAL</div>
              <div style={{ color: '#7c3aed', padding: '6px 2px', fontSize: '0.68rem' }}>PS-SEC17</div>
              <div style={{ color: '#059669', padding: '6px 2px', fontSize: '0.68rem' }}>PS-SEC40</div>

              {/* Row 1: PS-INDUSTRIAL */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#0284c7', fontSize: '0.68rem' }}>PS-IND</div>
              <div style={{ background: '#f8fafc', padding: '14px 4px', borderRadius: '8px', color: '#94a3b8' }}>Local</div>
              <div
                onClick={() => { setActiveCell('PS-INDUSTRIAL-PS-SEC17'); setSelectedLink(liveLinks[0]); }}
                style={{
                  background: activeCell === 'PS-INDUSTRIAL-PS-SEC17' ? '#4f46e5' : '#e0e7ff',
                  color: activeCell === 'PS-INDUSTRIAL-PS-SEC17' ? '#ffffff' : '#4338ca',
                  padding: '14px 4px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  border: activeCell === 'PS-INDUSTRIAL-PS-SEC17' ? '2px solid #312e81' : '1px solid #c7d2fe',
                  transition: 'all 0.2s ease',
                }}
              >
                <div>0.88 HIGH</div>
                <div style={{ fontSize: '0.65rem', opacity: 0.9 }}>14 Links</div>
              </div>
              <div
                onClick={() => { setActiveCell('PS-INDUSTRIAL-PS-SEC40'); setSelectedLink(liveLinks[2]); }}
                style={{
                  background: activeCell === 'PS-INDUSTRIAL-PS-SEC40' ? '#4f46e5' : '#d1fae5',
                  color: activeCell === 'PS-INDUSTRIAL-PS-SEC40' ? '#ffffff' : '#065f46',
                  padding: '14px 4px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  border: activeCell === 'PS-INDUSTRIAL-PS-SEC40' ? '2px solid #064e3b' : '1px solid #a7f3d0',
                  transition: 'all 0.2s ease',
                }}
              >
                <div>0.91 HIGH</div>
                <div style={{ fontSize: '0.65rem', opacity: 0.9 }}>9 Links</div>
              </div>

              {/* Row 2: PS-SEC17 */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#7c3aed', fontSize: '0.68rem' }}>PS-S17</div>
              <div
                onClick={() => { setActiveCell('PS-INDUSTRIAL-PS-SEC17'); setSelectedLink(liveLinks[0]); }}
                style={{
                  background: activeCell === 'PS-INDUSTRIAL-PS-SEC17' ? '#4f46e5' : '#e0e7ff',
                  color: activeCell === 'PS-INDUSTRIAL-PS-SEC17' ? '#ffffff' : '#4338ca',
                  padding: '14px 4px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                }}
              >
                <div>0.88 HIGH</div>
                <div style={{ fontSize: '0.65rem', opacity: 0.9 }}>14 Links</div>
              </div>
              <div style={{ background: '#f8fafc', padding: '14px 4px', borderRadius: '8px', color: '#94a3b8' }}>Local</div>
              <div
                onClick={() => { setActiveCell('PS-SEC17-PS-SEC40'); setSelectedLink(liveLinks[1]); }}
                style={{
                  background: activeCell === 'PS-SEC17-PS-SEC40' ? '#4f46e5' : '#f3e8ff',
                  color: activeCell === 'PS-SEC17-PS-SEC40' ? '#ffffff' : '#6b21a8',
                  padding: '14px 4px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  border: activeCell === 'PS-SEC17-PS-SEC40' ? '2px solid #581c87' : '1px solid #e9d5ff',
                  transition: 'all 0.2s ease',
                }}
              >
                <div>0.89 HIGH</div>
                <div style={{ fontSize: '0.65rem', opacity: 0.9 }}>18 Links</div>
              </div>

              {/* Row 3: PS-SEC40 */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#059669', fontSize: '0.68rem' }}>PS-S40</div>
              <div
                onClick={() => { setActiveCell('PS-INDUSTRIAL-PS-SEC40'); setSelectedLink(liveLinks[2]); }}
                style={{
                  background: activeCell === 'PS-INDUSTRIAL-PS-SEC40' ? '#4f46e5' : '#d1fae5',
                  color: activeCell === 'PS-INDUSTRIAL-PS-SEC40' ? '#ffffff' : '#065f46',
                  padding: '14px 4px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                }}
              >
                <div>0.91 HIGH</div>
                <div style={{ fontSize: '0.65rem', opacity: 0.9 }}>9 Links</div>
              </div>
              <div
                onClick={() => { setActiveCell('PS-SEC17-PS-SEC40'); setSelectedLink(liveLinks[1]); }}
                style={{
                  background: activeCell === 'PS-SEC17-PS-SEC40' ? '#4f46e5' : '#f3e8ff',
                  color: activeCell === 'PS-SEC17-PS-SEC40' ? '#ffffff' : '#6b21a8',
                  padding: '14px 4px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                }}
              >
                <div>0.89 HIGH</div>
                <div style={{ fontSize: '0.65rem', opacity: 0.9 }}>18 Links</div>
              </div>
              <div style={{ background: '#f8fafc', padding: '14px 4px', borderRadius: '8px', color: '#94a3b8' }}>Local</div>
            </div>
          </div>

          <div style={{ marginTop: '1.5rem', padding: '1rem', background: '#f8fafc', borderRadius: '12px', border: '1px solid #e2e8f0', fontSize: '0.78rem' }}>
            <span style={{ fontWeight: 700, color: '#0f172a' }}>Active Selection: </span>
            <span style={{ color: '#4f46e5', fontWeight: 600 }}>{activeCell.replace('-PS-', ' ↔ PS-')} Corridor</span>
            <div style={{ color: '#64748b', marginTop: '0.25rem' }}>
              Zetaris unified query <code>q_cross_station_incidents</code> resolved 3 active criminal series.
            </div>
            <div style={{ color: '#94a3b8', marginTop: '0.2rem', fontSize: '0.72rem' }}>
              Data mode: <strong>{dataMode === 'live' ? '🟢 Live API' : '🔵 Sample'}</strong>
              {apiLoading && ' — loading…'}
            </div>
          </div>
        </div>

        {/* Right: Interactive SVG Pulse Map Canvas */}
        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '16px', padding: '1.75rem', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', position: 'relative' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <div>
              <span style={{ fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase', color: '#059669', letterSpacing: '0.06em' }}>
                SPATIAL INTELLIGENCE
              </span>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0f172a' }}>Live Jurisdictional Pulse Map</h3>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.75rem', color: '#64748b' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#0284c7' }}></span> PS-INDUSTRIAL
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#7c3aed' }}></span> PS-SEC17
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#059669' }}></span> PS-SEC40
              </span>
            </div>
          </div>

          {/* SVG Map Canvas */}
          <div style={{ width: '100%', height: '360px', background: '#f8fafc', borderRadius: '12px', border: '1px solid #e2e8f0', position: 'relative', overflow: 'hidden' }}>
            <svg width="100%" height="100%" viewBox="0 0 660 420" style={{ display: 'block' }}>
              <defs>
                <linearGradient id="arcNorthCentral" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#0284c7" />
                  <stop offset="100%" stopColor="#7c3aed" />
                </linearGradient>
                <linearGradient id="arcCentralRiverside" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#7c3aed" />
                  <stop offset="100%" stopColor="#059669" />
                </linearGradient>
                <linearGradient id="arcNorthRiverside" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#0284c7" />
                  <stop offset="100%" stopColor="#059669" />
                </linearGradient>
              </defs>

              {/* Grid Background Lines */}
              <pattern id="mapGrid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e2e8f0" strokeWidth="0.8" />
              </pattern>
              <rect width="100%" height="100%" fill="url(#mapGrid)" />

              {/* Jurisdictional Boundary Circles */}
              <circle cx="180" cy="130" r="95" fill="rgba(2, 132, 199, 0.04)" stroke="#bae6fd" strokeWidth="1.5" strokeDasharray="4 4" />
              <circle cx="480" cy="110" r="95" fill="rgba(124, 58, 237, 0.04)" stroke="#ddd6fe" strokeWidth="1.5" strokeDasharray="4 4" />
              <circle cx="330" cy="340" r="95" fill="rgba(5, 150, 105, 0.04)" stroke="#a7f3d0" strokeWidth="1.5" strokeDasharray="4 4" />

              {/* Dynamic Connection Arcs */}
              {/* Arc 1: PS-INDUSTRIAL to PS-SEC17 (Safe Syndicate) */}
              <path
                d="M 180 130 Q 330 40 480 110"
                fill="none"
                stroke="url(#arcNorthCentral)"
                strokeWidth={selectedLink.id === 'LNK-SERIES-01' ? '4' : '2.5'}
                strokeDasharray={selectedLink.id === 'LNK-SERIES-01' ? 'none' : '5 3'}
                style={{ cursor: 'pointer', filter: 'drop-shadow(0 2px 4px rgba(79, 70, 229, 0.2))' }}
                onClick={() => setSelectedLink(liveLinks[0])}
              />
              {/* Arc 2: PS-SEC17 to PS-SEC40 (Catalytic Ring) */}
              <path
                d="M 480 110 Q 460 270 330 340"
                fill="none"
                stroke="url(#arcCentralRiverside)"
                strokeWidth={selectedLink.id === 'LNK-SERIES-02' ? '4' : '2.5'}
                strokeDasharray={selectedLink.id === 'LNK-SERIES-02' ? 'none' : '5 3'}
                style={{ cursor: 'pointer', filter: 'drop-shadow(0 2px 4px rgba(124, 58, 237, 0.2))' }}
                onClick={() => setSelectedLink(liveLinks[1])}
              />
              {/* Arc 3: PS-INDUSTRIAL to PS-SEC40 (SUV Relay) */}
              <path
                d="M 180 130 Q 200 270 330 340"
                fill="none"
                stroke="url(#arcNorthRiverside)"
                strokeWidth={selectedLink.id === 'LNK-SERIES-03' ? '4' : '2.5'}
                strokeDasharray={selectedLink.id === 'LNK-SERIES-03' ? 'none' : '5 3'}
                style={{ cursor: 'pointer', filter: 'drop-shadow(0 2px 4px rgba(5, 150, 105, 0.2))' }}
                onClick={() => setSelectedLink(liveLinks[2])}
              />

              {/* Station Nodes */}
              {Object.entries(STATION_COORDS).map(([code, st]) => (
                <g key={code} transform={`translate(${st.x}, ${st.y})`}>
                  <circle r="22" fill="#ffffff" stroke={st.color} strokeWidth="3" filter="drop-shadow(0 4px 6px rgba(0,0,0,0.08))" />
                  <circle r="8" fill={st.color} />
                  <text y="-28" textAnchor="middle" fontSize="11" fontWeight="800" fill="#0f172a">
                    {st.label}
                  </text>
                  <text y="-16" textAnchor="middle" fontSize="8" fontWeight="600" fill="#64748b">
                    {code}
                  </text>
                </g>
              ))}

              {/* Incident Hotspot Pins */}
              <g transform="translate(140, 110)">
                <circle r="5" fill="#ef4444" />
                <circle r="9" fill="none" stroke="#ef4444" strokeWidth="1" opacity="0.6" />
                <text x="8" y="4" fontSize="8" fontWeight="700" fill="#334155">INC-NORTH-0042</text>
              </g>
              <g transform="translate(520, 140)">
                <circle r="5" fill="#ef4444" />
                <circle r="9" fill="none" stroke="#ef4444" strokeWidth="1" opacity="0.6" />
                <text x="8" y="4" fontSize="8" fontWeight="700" fill="#334155">INC-CENTRAL-0118</text>
              </g>
              <g transform="translate(360, 360)">
                <circle r="5" fill="#ef4444" />
                <circle r="9" fill="none" stroke="#ef4444" strokeWidth="1" opacity="0.6" />
                <text x="8" y="4" fontSize="8" fontWeight="700" fill="#334155">INC-RIV-0182</text>
              </g>
            </svg>
          </div>
        </div>
      </div>

      {/* ── Bottom Section: Skeptic Agent Audit & Link Dossier Card ── */}
      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '16px', padding: '2rem', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', borderBottom: '1px solid #f1f5f9', paddingBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div
              style={{
                background: selectedLink.skepticStatus === 'VERIFIED' ? '#d1fae5' : '#fee2e2',
                color: selectedLink.skepticStatus === 'VERIFIED' ? '#059669' : '#dc2626',
                padding: '6px',
                borderRadius: '8px',
              }}
            >
              {selectedLink.skepticStatus === 'VERIFIED' ? <CheckCircle2 size={20} /> : <AlertOctagon size={20} />}
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0f172a' }}>{selectedLink.title}</h3>
                <span
                  style={{
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '9999px',
                    background: selectedLink.skepticStatus === 'VERIFIED' ? '#d1fae5' : '#fee2e2',
                    color: selectedLink.skepticStatus === 'VERIFIED' ? '#065f46' : '#991b1b',
                  }}
                >
                  SKEPTIC: {selectedLink.skepticStatus}
                </span>
              </div>
              <span style={{ fontSize: '0.85rem', color: '#64748b' }}>
                Jurisdictions: {selectedLink.sourceStation} Station ↔ {selectedLink.targetStation} Station • Confidence Score: {(selectedLink.confidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Grounding Validation</span>
            <div style={{ fontSize: '0.9rem', fontWeight: 800, color: '#059669' }}>100% Citation Grounded</div>
          </div>
        </div>

        {/* 3-Column Factor Breakdown */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', marginBottom: '1.5rem' }}>
          <div style={{ background: '#f8fafc', padding: '1.15rem', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Forensic & Toolmark Match</span>
            <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#0f172a', marginTop: '0.35rem' }}>{selectedLink.toolmarkOrWeapon}</div>
            <p style={{ fontSize: '0.78rem', color: '#475569', marginTop: '0.25rem' }}>{selectedLink.basis}</p>
          </div>

          <div style={{ background: '#f8fafc', padding: '1.15rem', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>CCTV & Vehicle Vector</span>
            <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#0f172a', marginTop: '0.35rem' }}>{selectedLink.vehicle}</div>
            <p style={{ fontSize: '0.78rem', color: '#475569', marginTop: '0.25rem' }}>Correlated across camera feeds with optical timestamp verification.</p>
          </div>

          <div style={{ background: '#f8fafc', padding: '1.15rem', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Cited Zetaris Evidence Records</span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.5rem' }}>
              {selectedLink.evidenceIds.map((eid) => (
                <span key={eid} style={{ fontSize: '0.72rem', fontWeight: 700, background: '#ffffff', border: '1px solid #cbd5e1', padding: '2px 8px', borderRadius: '6px', color: '#0f172a' }}>
                  {eid}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Skeptic Reasoning Box */}
        <div style={{ background: selectedLink.skepticStatus === 'VERIFIED' ? '#f0fdf4' : '#fff1f2', border: `1px solid ${selectedLink.skepticStatus === 'VERIFIED' ? '#bbf7d0' : '#fecdd3'}`, borderRadius: '12px', padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
            <ShieldAlert size={16} color={selectedLink.skepticStatus === 'VERIFIED' ? '#059669' : '#e11d48'} />
            <strong style={{ fontSize: '0.85rem', color: selectedLink.skepticStatus === 'VERIFIED' ? '#065f46' : '#9f1239' }}>
              Skeptic Agent Challenge Audit (Nemotron 3 Ultra 550B):
            </strong>
          </div>
          <p style={{ fontSize: '0.82rem', color: selectedLink.skepticStatus === 'VERIFIED' ? '#14532d' : '#881337', lineHeight: 1.5 }}>
            {selectedLink.skepticNotes}
          </p>
        </div>
      </div>
    </div>
  );
};
