import React, { useEffect, useState } from 'react';
import {
  BrainCircuit,
  Search,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  Database,
  Cpu,
  Activity,
  Camera,
  Eye,
  Microscope,
  Newspaper,
  RefreshCw,
  ShieldCheck,
  Download,
  FileText,
} from 'lucide-react';
import {
  AIDiagnosticResponse,
  EngineHealthResponse,
  InvestigationResponse,
  SampleScenarioMeta,
} from '../types';
import { api } from '../services/api';
import { AgentRunPanel } from '../components/AgentRunPanel';

export const InvestigationPage: React.FC = () => {
  const [query, setQuery] = useState<string>(
    'Investigate commercial safe burglaries in North and Central involving crowbar prying and grey minivan'
  );
  const [selectedStations, setSelectedStations] = useState<string[]>(['NORTH', 'CENTRAL', 'RIVERSIDE']);
  const [crimeType, setCrimeType] = useState<string>('ALL');
  const [useSampleMode, setUseSampleMode] = useState<boolean>(false);
  const [sampleScenarios, setSampleScenarios] = useState<SampleScenarioMeta[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('crowbar_safe_cracking');

  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<InvestigationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Diagnostics state
  const [showDiagnostics, setShowDiagnostics] = useState<boolean>(false);
  const [aiDiag, setAiDiag] = useState<AIDiagnosticResponse | null>(null);
  const [engineHealth, setEngineHealth] = useState<EngineHealthResponse | null>(null);
  const [probingDiag, setProbingDiag] = useState<boolean>(false);

  // Expanded evidence state
  const [expandedEvidenceSource, setExpandedEvidenceSource] = useState<string | null>('forensic_reports');

  useEffect(() => {
    api
      .getSampleScenarios()
      .then(setSampleScenarios)
      .catch((err) => console.error('Failed to load sample scenarios:', err));

    // Initial probe of AI and engine health
    probeDiagnostics();
  }, []);

  const probeDiagnostics = () => {
    setProbingDiag(true);
    Promise.all([
      api.getAIDiagnostic().catch((err) => ({
        status: 'error',
        configured: false,
        message: err.message,
      })),
      api.getEngineHealth().catch((err) => ({
        status: 'error',
        engine: 'meterless_world_model',
        configured: false,
        engine_path: '',
        world_dir: '',
        message: err.message,
      })),
    ])
      .then(([aiRes, engRes]) => {
        setAiDiag(aiRes as AIDiagnosticResponse);
        setEngineHealth(engRes as EngineHealthResponse);
      })
      .finally(() => setProbingDiag(false));
  };

  const toggleStation = (station: string) => {
    if (selectedStations.includes(station)) {
      if (selectedStations.length > 1) {
        setSelectedStations(selectedStations.filter((s) => s !== station));
      }
    } else {
      setSelectedStations([...selectedStations, station]);
    }
  };

  const handleSelectScenario = (sc: SampleScenarioMeta) => {
    setSelectedScenarioId(sc.scenario_id);
    setQuery(sc.query);
    setSelectedStations(sc.target_stations);
    setCrimeType(sc.crime_type);
    setUseSampleMode(true);
  };

  const handleRunInvestigation = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const resp = await api.analyzeInvestigation({
        query: query.trim(),
        station_ids: selectedStations,
        crime_type: crimeType !== 'ALL' ? crimeType : undefined,
        sample_mode: useSampleMode,
        scenario_id: useSampleMode ? selectedScenarioId : undefined,
      });
      setResult(resp);
    } catch (err: any) {
      setError(err.message || 'Failed to complete investigation analysis.');
    } finally {
      setLoading(false);
    }
  };

  const handleResume = async (runId: string) => {
    setLoading(true);
    setError(null);
    try {
      setResult(await api.analyzeInvestigation({ query: query.trim() || 'continue', continue_from: runId, sample_mode: false }));
    } catch (err: any) {
      setError(err.message || 'Failed to resume investigation.');
    } finally {
      setLoading(false);
    }
  };

  const handleExportDossier = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `dossier-${result.investigation_id || 'export'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handlePrintDossier = () => {
    window.print();
  };

  return (
    <div className="investigation-page" style={{ padding: '1.5rem 2rem', maxWidth: '1440px', margin: '0 auto' }}>
      {/* ── Page Header ────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem' }}>
            <div style={{ background: 'var(--accent-purple)', padding: '6px', borderRadius: '8px', color: '#fff' }}>
              <BrainCircuit size={22} />
            </div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '0.02em' }}>
              INVESTIGATION WORKBENCH
            </h1>
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                padding: '2px 8px',
                borderRadius: '12px',
                background: 'rgba(168, 85, 247, 0.15)',
                color: 'var(--accent-purple)',
                border: '1px solid rgba(168, 85, 247, 0.3)',
              }}
            >
              Multi-Agent Intelligence Hub
            </span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: '850px' }}>
            Coordinate Planner, Finder, Skeptic, and Reporter agents across North, Central, and Riverside
            jurisdictions. Queries real Zetaris SQL, checks every citation deterministically, shares state via the Meterless
            engines, and routes all model calls through Nightshift (NVIDIA Nemotron).
          </p>
        </div>

        {/* Integration Status Badges */}
        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
          <button
            onClick={() => setShowDiagnostics(!showDiagnostics)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '8px',
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-secondary)',
              fontSize: '0.8rem',
              cursor: 'pointer',
            }}
          >
            <Activity size={14} className={probingDiag ? 'spin' : ''} />
            Diagnostics {showDiagnostics ? '▲' : '▼'}
          </button>
        </div>
      </div>

      {/* ── Diagnostics Panel (Collapsible) ─────────────────────────────────── */}
      {showDiagnostics && (
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '10px',
            padding: '1rem',
            marginBottom: '1.5rem',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '1rem',
          }}
        >
          {/* Nightshift + Nemotron */}
          <div style={{ background: 'var(--bg-elevated)', padding: '0.8rem', borderRadius: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Cpu size={14} color="var(--accent-blue)" /> Nightshift / NVIDIA Nemotron
              </span>
              <span
                style={{
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  padding: '2px 6px',
                  borderRadius: '4px',
                  background: aiDiag?.status === 'connected' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.2)',
                  color: aiDiag?.status === 'connected' ? 'var(--accent-emerald)' : 'var(--accent-rose)',
                }}
              >
                {aiDiag?.status?.toUpperCase() || 'UNKNOWN'}
              </span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              <div>Model: <code style={{ color: 'var(--text-primary)' }}>{aiDiag?.model || 'nvidia/nemotron-3.5-lightning-30b-a3b'}</code></div>
              <div>Provider: <code style={{ color: 'var(--accent-blue)' }}>{aiDiag?.provider || 'nvidia'}</code></div>
              <div>Latency: {aiDiag?.latency_ms ? `${aiDiag.latency_ms}ms` : 'N/A'}</div>
            </div>
          </div>

          {/* Meterless World Model */}
          <div style={{ background: 'var(--bg-elevated)', padding: '0.8rem', borderRadius: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <BrainCircuit size={14} color="var(--accent-purple)" /> Meterless World Model
              </span>
              <span
                style={{
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  padding: '2px 6px',
                  borderRadius: '4px',
                  background: engineHealth?.status === 'connected' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.2)',
                  color: engineHealth?.status === 'connected' ? 'var(--accent-emerald)' : 'var(--accent-rose)',
                }}
              >
                {engineHealth?.status?.toUpperCase() || 'UNKNOWN'}
              </span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              <div>Engine: <code style={{ color: 'var(--text-primary)' }}>{engineHealth?.engine || 'meterless_world_model'}</code></div>
              <div>Schema Version: {engineHealth?.schema_version ?? 1}</div>
              <div>Storage: File-backed (runtime/world)</div>
            </div>
          </div>

          {/* Zetaris Data Layer */}
          <div style={{ background: 'var(--bg-elevated)', padding: '0.8rem', borderRadius: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Database size={14} color="var(--accent-cyan)" /> Zetaris NDP SQL Layer
              </span>
              <span
                style={{
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  padding: '2px 6px',
                  borderRadius: '4px',
                  background: 'rgba(16, 185, 129, 0.2)',
                  color: 'var(--accent-emerald)',
                }}
              >
                LIVE (5 TABLES)
              </span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              <div>Mode: <code style={{ color: 'var(--accent-emerald)' }}>zetaris_live</code></div>
              <div>Tables: 5 registered (10,000 synthetic records)</div>
              <div>Query Type: Real parameterized SQL</div>
            </div>
          </div>
        </div>
      )}

      {/* ── Query & Investigation Control Panel ───────────────────────────── */}
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '12px',
          padding: '1.2rem',
          marginBottom: '1.5rem',
        }}
      >
        {/* Preset Sample Scenarios Buttons */}
        <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.8rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>
            Preset Scenarios:
          </span>
          {sampleScenarios.map((sc) => (
            <button
              key={sc.scenario_id}
              onClick={() => handleSelectScenario(sc)}
              style={{
                fontSize: '0.75rem',
                padding: '4px 10px',
                borderRadius: '6px',
                background: selectedScenarioId === sc.scenario_id && useSampleMode ? 'var(--accent-blue-glow)' : 'var(--bg-elevated)',
                color: selectedScenarioId === sc.scenario_id && useSampleMode ? 'var(--accent-blue)' : 'var(--text-secondary)',
                border: selectedScenarioId === sc.scenario_id && useSampleMode ? '1px solid var(--accent-blue)' : '1px solid var(--border-subtle)',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {sc.title}
            </button>
          ))}
        </div>

        {/* Input Form */}
        <form onSubmit={handleRunInvestigation}>
          <div style={{ display: 'flex', gap: '0.8rem', marginBottom: '1rem' }}>
            <div style={{ position: 'relative', flex: 1 }}>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter investigative inquiry (e.g. safe burglaries, catalytic converter thefts, push-to-start relay attacks)..."
                style={{
                  width: '100%',
                  padding: '10px 14px 10px 38px',
                  background: 'var(--bg-darkest)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  color: 'var(--text-primary)',
                  fontSize: '0.9rem',
                }}
              />
              <Search
                size={16}
                style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}
              />
            </div>

            <button
              type="submit"
              disabled={loading || !query.trim()}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '0 20px',
                background: 'linear-gradient(135deg, #a855f7, #6366f1)',
                color: '#fff',
                border: 'none',
                borderRadius: '8px',
                fontWeight: 600,
                fontSize: '0.9rem',
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.7 : 1,
                boxShadow: '0 2px 10px rgba(168, 85, 247, 0.3)',
              }}
            >
              {loading ? (
                <>
                  <RefreshCw size={16} className="spin" />
                  Analyzing Multi-Station Evidence...
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  Run Autonomous Investigation
                </>
              )}
            </button>
          </div>

          {/* Filtering options */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
            {/* Stations Selection */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Target Stations:</span>
              {[
                { id: 'NORTH', label: 'PS-INDUSTRIAL' },
                { id: 'CENTRAL', label: 'PS-SEC17' },
                { id: 'RIVERSIDE', label: 'PS-SEC40' },
              ].map(({ id, label }) => (
                <button
                  type="button"
                  key={id}
                  onClick={() => toggleStation(id)}
                  style={{
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    padding: '3px 8px',
                    borderRadius: '4px',
                    background: selectedStations.includes(id) ? 'var(--bg-elevated)' : 'transparent',
                    color: selectedStations.includes(id) ? 'var(--text-primary)' : 'var(--text-muted)',
                    border: selectedStations.includes(id) ? '1px solid var(--border-glow)' : '1px solid var(--border-subtle)',
                    cursor: 'pointer',
                  }}
                  title={`${label} (${id})`}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Mode selection toggle */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.8rem',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={useSampleMode}
                  onChange={(e) => setUseSampleMode(e.target.checked)}
                />
                Sample Mode (Planted Scenarios)
              </label>

              <span
                style={{
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  padding: '2px 8px',
                  borderRadius: '4px',
                  background: useSampleMode ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                  color: useSampleMode ? 'var(--accent-amber)' : 'var(--accent-emerald)',
                  border: useSampleMode ? '1px solid rgba(245, 158, 11, 0.3)' : '1px solid rgba(16, 185, 129, 0.3)',
                }}
              >
                {useSampleMode ? 'SIMULATED DATA' : 'LIVE ZETARIS + NIGHTSHIFT'}
              </span>
            </div>
          </div>
        </form>
      </div>

      {/* ── Error Banner ──────────────────────────────────────────────────── */}
      {error && (
        <div
          style={{
            background: 'rgba(244, 63, 94, 0.15)',
            border: '1px solid var(--accent-rose)',
            borderRadius: '10px',
            padding: '1rem',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px',
            color: '#fecdd3',
          }}
        >
          <AlertTriangle size={20} color="var(--accent-rose)" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <div style={{ fontWeight: 600, marginBottom: '2px' }}>Investigation Execution Refused</div>
            <div style={{ fontSize: '0.85rem' }}>{error}</div>
          </div>
        </div>
      )}

      {/* ── Loading Spinner ───────────────────────────────────────────────── */}
      {loading && (
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '12px',
            padding: '3rem 2rem',
            textAlign: 'center',
            marginBottom: '1.5rem',
          }}
        >
          <div style={{ marginBottom: '1rem' }}>
            <BrainCircuit size={48} className="spin" color="var(--accent-purple)" />
          </div>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '0.5rem' }}>
            Autonomous Multi-Agent Investigation in Progress
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', maxWidth: '600px', margin: '0 auto 1.5rem' }}>
            Scout Intent routes the request • Planner plans retrieval • Finder queries Zetaris SQL and proposes links •
            deterministic verifier checks every citation • Skeptic challenges the links and may trigger more retrieval •
            Reporter writes from validated state. This can take a few minutes; progress details appear when the run ends.
          </p>
          <div style={{ display: 'inline-flex', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <span>Models via Nightshift</span> • <span>Zetaris: Live Query</span> • <span>Meterless Engines: World Model, H-MEM, Scout Intent, Markovian</span>
          </div>
        </div>
      )}

      {/* ── Investigation Results ─────────────────────────────────────────── */}
      {result && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Executive Summary Card */}
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '12px',
              padding: '1.5rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.3rem' }}>
                  <h2 style={{ fontSize: '1.3rem', fontWeight: 700 }}>{result.title}</h2>
                  <span
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: '4px',
                      background: result.is_sample ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                      color: result.is_sample ? 'var(--accent-amber)' : 'var(--accent-emerald)',
                      border: result.is_sample ? '1px solid rgba(245, 158, 11, 0.3)' : '1px solid rgba(16, 185, 129, 0.3)',
                    }}
                  >
                    {result.is_sample ? 'SAMPLE MODE' : 'LIVE INTEGRATION EXECUTION'}
                  </span>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Run ID: <code style={{ color: 'var(--text-secondary)' }}>{result.investigation_id}</code>
                  {result.elapsed_seconds && ` • Elapsed: ${result.elapsed_seconds}s`}
                  {result.trace_file && ` • Trace: ${result.trace_file}`}
                </div>
              </div>

              {/* Stations involved badges and actions */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', gap: '6px' }}>
                  {result.stations_involved.map((st) => (
                    <span
                      key={st}
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        padding: '4px 8px',
                        borderRadius: '4px',
                        background: 'var(--bg-elevated)',
                        color: 'var(--accent-blue)',
                        border: '1px solid var(--border-subtle)',
                      }}
                    >
                      {st} PRECINCT
                    </span>
                  ))}
                </div>

                <button
                  type="button"
                  onClick={handleExportDossier}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '5px 10px',
                    borderRadius: '6px',
                    background: '#4f46e5',
                    color: '#ffffff',
                    border: 'none',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                  title="Export complete dossier and evidence graph to JSON"
                >
                  <Download size={13} />
                  Export Dossier (JSON)
                </button>

                <button
                  type="button"
                  onClick={handlePrintDossier}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '5px 10px',
                    borderRadius: '6px',
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                  title="Print dossier view"
                >
                  <FileText size={13} />
                  Print View
                </button>
              </div>
            </div>

            {/* Executive summary body */}
            <p
              style={{
                color: 'var(--text-primary)',
                fontSize: '0.95rem',
                lineHeight: 1.6,
                background: 'var(--bg-elevated)',
                padding: '1rem 1.2rem',
                borderRadius: '8px',
                borderLeft: '4px solid var(--accent-purple)',
              }}
            >
              {result.executive_summary}
            </p>
          </div>

          <AgentRunPanel result={result} onResume={handleResume} />

          {/* Candidate Links (The Primary Findings) */}
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '12px',
              padding: '1.5rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1.2rem' }}>
              <ShieldCheck size={20} color="var(--accent-emerald)" />
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                Candidate Cross-Station Links ({result.candidate_links.length})
              </h3>
            </div>

            {result.candidate_links.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                No candidate links met the strict physical or forensic evidence threshold across jurisdictions.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {result.candidate_links.map((link) => (
                  <div
                    key={link.link_id}
                    style={{
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '10px',
                      padding: '1.2rem',
                    }}
                  >
                    {/* Link header */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--accent-blue)' }}>
                          {link.source_incident_id}
                        </span>
                        <ArrowRight size={16} color="var(--text-muted)" />
                        <span style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--accent-cyan)' }}>
                          {link.target_incident_id}
                        </span>
                      </div>

                      {link.validation_status && (
                        <span title={link.validation_explanation ?? ''} style={{ fontSize: '0.72rem', fontWeight: 700, padding: '3px 10px', borderRadius: '12px',
                          marginRight: '8px', border: '1px solid var(--border-subtle)',
                          color: link.validation_status === 'SUPPORTED' ? 'var(--accent-emerald)' : link.validation_status === 'WEAK' ? 'var(--accent-amber)' : 'var(--accent-rose)' }}>
                          Verifier: {link.validation_status} • {link.independent_source_count ?? 0} independent source(s)
                          {link.withdrawn ? ' • withdrawn by Finder' : ''}
                        </span>
                      )}
                      {/* Confidence Score Pill */}
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          background: 'rgba(16, 185, 129, 0.15)',
                          padding: '3px 10px',
                          borderRadius: '12px',
                          border: '1px solid rgba(16, 185, 129, 0.3)',
                        }}
                        title={link.confidence_rationale}
                      >
                        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Heuristic score (uncalibrated, not a probability):</span>
                        <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-emerald)' }}>
                          {Math.round(link.confidence_score * 100)}%
                        </span>
                      </div>
                    </div>

                    {/* Similarity Basis */}
                    <div style={{ marginBottom: '0.8rem', fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                      <strong>Link Basis:</strong> {link.similarity_basis}
                    </div>

                    {/* Supporting Evidence Chips */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', marginBottom: '0.8rem' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Citations:</span>
                      {link.supporting_evidence_ids.map((evId) => (
                        <span
                          key={evId}
                          style={{
                            fontSize: '0.75rem',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            background: 'var(--bg-darkest)',
                            color: 'var(--accent-blue)',
                            border: '1px solid var(--border-subtle)',
                            fontFamily: 'var(--font-mono)',
                          }}
                        >
                          {evId}
                        </span>
                      ))}
                    </div>

                    {/* Contradictions for this link */}
                    {link.contradictions && link.contradictions.length > 0 && (
                      <div
                        style={{
                          background: 'rgba(244, 63, 94, 0.1)',
                          border: '1px solid rgba(244, 63, 94, 0.3)',
                          borderRadius: '6px',
                          padding: '0.6rem 0.8rem',
                          marginTop: '0.5rem',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-rose)', fontSize: '0.75rem', fontWeight: 700, marginBottom: '2px' }}>
                          <AlertTriangle size={13} /> CONTRADICTORY OBSERVATIONS (kept visible):
                        </div>
                        {link.contradictions.map((c, i) => (
                          <div key={i} style={{ fontSize: '0.8rem', color: '#fecdd3' }}>
                            {c.description} {(c.source_id || (c as any).source_ids?.length) && `(Source: ${c.source_id || (c as any).source_ids.join(', ')})`}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Contradictions, Limitations & Follow-ups Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '1.5rem' }}>
            {/* Contradictions & Uncertainty */}
            <div
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '12px',
                padding: '1.2rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.8rem' }}>
                <AlertTriangle size={18} color="var(--accent-amber)" />
                <h4 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Contradictions & Limitations</h4>
              </div>
              <ul style={{ paddingLeft: '1.2rem', fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {result.contradictions_and_limitations.map((lim, idx) => (
                  <li key={idx}>{lim}</li>
                ))}
              </ul>
            </div>

            {/* Recommended Follow-up Actions */}
            <div
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '12px',
                padding: '1.2rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.8rem' }}>
                <CheckCircle2 size={18} color="var(--accent-cyan)" />
                <h4 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Recommended Follow-up Steps</h4>
              </div>
              <ol style={{ paddingLeft: '1.2rem', fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {result.follow_up_actions.map((act, idx) => (
                  <li key={idx}>{act}</li>
                ))}
              </ol>
            </div>
          </div>

          {/* Evidence Vault (Raw Supporting Records) */}
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '12px',
              padding: '1.2rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Database size={18} color="var(--accent-blue)" />
                <h4 style={{ fontSize: '1rem', fontWeight: 700 }}>Retrieved Evidence Vault</h4>
              </div>

              {/* Source switcher tabs */}
              <div style={{ display: 'flex', gap: '4px' }}>
                {[
                  { id: 'forensic_reports', label: 'Forensic', icon: Microscope, count: result.supporting_evidence.forensic_reports?.length || 0 },
                  { id: 'cctv_reports', label: 'CCTV', icon: Camera, count: result.supporting_evidence.cctv_reports?.length || 0 },
                  { id: 'witness_reports', label: 'Witness', icon: Eye, count: result.supporting_evidence.witness_reports?.length || 0 },
                  { id: 'newspaper_reports', label: 'News', icon: Newspaper, count: result.supporting_evidence.newspaper_reports?.length || 0 },
                ].map((s) => (
                  <button
                    key={s.id}
                    onClick={() => setExpandedEvidenceSource(s.id)}
                    style={{
                      fontSize: '0.75rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                      padding: '4px 10px',
                      borderRadius: '6px',
                      background: expandedEvidenceSource === s.id ? 'var(--bg-elevated)' : 'transparent',
                      color: expandedEvidenceSource === s.id ? 'var(--accent-blue)' : 'var(--text-muted)',
                      border: expandedEvidenceSource === s.id ? '1px solid var(--border-glow)' : '1px solid transparent',
                      cursor: 'pointer',
                    }}
                  >
                    <s.icon size={13} />
                    {s.label} ({s.count})
                  </button>
                ))}
              </div>
            </div>

            {/* Evidence items list */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '0.8rem' }}>
              {expandedEvidenceSource &&
                (result.supporting_evidence as any)[expandedEvidenceSource]?.map((rec: any, idx: number) => {
                  const id =
                    rec.evidence_report_id || rec.cctv_report_id || rec.witness_report_id || rec.news_id || `rec-${idx}`;
                  return (
                    <div
                      key={id}
                      style={{
                        background: 'var(--bg-darkest)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '8px',
                        padding: '0.8rem',
                        fontSize: '0.8rem',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontWeight: 700, color: 'var(--accent-blue)', fontFamily: 'var(--font-mono)' }}>{id}</span>
                        {rec.location_id && <span style={{ color: 'var(--text-muted)' }}>{rec.location_id}</span>}
                      </div>

                      <p style={{ color: 'var(--text-secondary)', fontSize: '0.78rem', marginBottom: '6px' }}>
                        {rec.result_summary || rec.movement_description || rec.observation_text || rec.headline || rec.description}
                      </p>

                      <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                        <span>
                          {rec.evidence_type || rec.vehicle_description || rec.publication_name || 'Evidence record'}
                        </span>
                        {rec.confidence_level && <span>Confidence: {rec.confidence_level}</span>}
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
