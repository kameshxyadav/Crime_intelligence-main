import React from 'react';
import { AlertTriangle, Brain, Cpu, GitBranch, ShieldAlert } from 'lucide-react';
import { InvestigationResponse } from '../types';

const card: React.CSSProperties = {
  background: 'var(--bg-card)',
  border: '1px solid var(--border-subtle)',
  borderRadius: '12px',
  padding: '1.2rem',
};
const chip = (color: string): React.CSSProperties => ({
  fontSize: '0.7rem', fontWeight: 600, padding: '2px 8px', borderRadius: '10px',
  background: 'var(--bg-darkest)', color, border: '1px solid var(--border-subtle)',
});
const mono: React.CSSProperties = { fontFamily: 'var(--font-mono)', fontSize: '0.72rem' };
const ENGINE_LABEL: Record<string, string> = {
  scout: 'Scout Intent', hmem: 'H-MEM', markovian: 'Markovian', world_model: 'World Model',
};

/** Shows what actually ran: agents, models that answered, engine operations, objections, stop reason. */
export const AgentRunPanel: React.FC<{ result: InvestigationResponse; onResume?: (id: string) => void }> = ({ result, onResume }) => {
  if (result.is_sample) {
    return (
      <div style={{ ...card, borderColor: 'rgba(245, 158, 11, 0.4)' }}>
        <strong style={{ color: 'var(--accent-amber)' }}>SAMPLE MODE</strong>
        <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginLeft: 8 }}>
          Pre-built scenario. No agents, models, Zetaris queries or Meterless Engines ran for this result.
        </span>
      </div>
    );
  }
  if (!result.agents && !result.engine_operations) return null;

  const objections = result.skeptic?.objections ?? [];
  const open = objections.filter((o) => o.open);
  const engines = (result.engine_operations ?? []).reduce<Record<string, { ops: Set<string>; calls: number; bad: number }>>((acc, o) => {
    const e = (acc[o.engine] ??= { ops: new Set(), calls: 0, bad: 0 });
    e.ops.add(o.op); e.calls += 1; if (o.status !== 'ok') e.bad += 1;
    return acc;
  }, {});
  const wm = result.integration_status?.meterless_engines?.world_model as any;
  const status = result.run_status ?? 'unknown';
  const statusColor = status === 'completed' ? 'var(--accent-emerald)' : status === 'blocked' || status === 'refused' ? 'var(--accent-rose)' : 'var(--accent-amber)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={card}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: '0.8rem' }}>
          <GitBranch size={18} color="var(--accent-purple)" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Run Progress</h3>
          <span style={{ ...chip(statusColor), border: `1px solid ${statusColor}` }}>{status.toUpperCase()}</span>
          {result.intent && <span style={chip('var(--accent-blue)')}>intent: {result.intent}</span>}
          {result.counts && (
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {result.counts.iterations} iteration(s) • {result.counts.model_calls} model call(s) • {result.counts.sql_queries} SQL queries
            </span>
          )}
        </div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>
          Stopping reason: <code style={{ color: 'var(--text-primary)' }}>{result.stopping_reason}</code>
        </div>
        {result.resume_hint && onResume && (
          <button onClick={() => onResume(result.investigation_id)}
            style={{ fontSize: '0.8rem', padding: '5px 12px', borderRadius: 6, border: '1px solid var(--accent-amber)', background: 'transparent', color: 'var(--accent-amber)', cursor: 'pointer', marginBottom: '0.6rem' }}>
            Resume this investigation
          </button>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {(result.iterations ?? []).map((it) => (
            <div key={it.iteration} style={{ background: 'var(--bg-elevated)', borderRadius: 8, padding: '0.5rem 0.8rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--text-primary)' }}>Iteration {it.iteration}</strong> — {(it.agents as string[]).join(' → ')}
              {' • '}retrieved {it.new_incidents} incident(s), {it.new_evidence} evidence record(s)
              {it.skeptic && <> • Skeptic: <code>{it.skeptic}</code></>}
              {it.next_action && <> • next: <code>{it.next_action}</code></>}
              {it.planner_fallback && <span style={{ color: 'var(--accent-amber)' }}> • planner fallback used</span>}
            </div>
          ))}
        </div>
      </div>

      {(result.partial_failures?.length ?? 0) > 0 && (
        <div style={{ ...card, borderColor: 'rgba(245, 158, 11, 0.4)' }}>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center', color: 'var(--accent-amber)', fontWeight: 700, fontSize: '0.85rem', marginBottom: 6 }}>
            <AlertTriangle size={15} /> Partial failures / degraded steps
          </div>
          {result.partial_failures!.map((f, i) => (
            <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}><code>{f.component}</code>: {f.message}</div>
          ))}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
        <div style={card}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <Cpu size={16} color="var(--accent-blue)" /><h4 style={{ fontSize: '0.9rem', fontWeight: 700 }}>Agents &amp; models that actually ran</h4>
          </div>
          {(result.agents ?? []).map((a) => (
            <div key={a.agent} style={{ marginBottom: 8, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--text-primary)', textTransform: 'capitalize' }}>{a.agent}</strong> ({a.calls} call{a.calls === 1 ? '' : 's'}, avg {Math.round(a.avg_latency_ms)} ms)
              <div style={mono}>answered by: {a.reported_models.join(', ') || '—'}</div>
              {a.fallback_used && (
                <div style={{ color: 'var(--accent-amber)', fontSize: '0.75rem' }}>
                  fallback used — {a.fallback_reasons[0] ?? 'specialist model unavailable'}
                </div>
              )}
              {a.errors.length > 0 && <div style={{ color: 'var(--accent-rose)', fontSize: '0.75rem' }}>{a.errors[0]}</div>}
            </div>
          ))}
        </div>

        <div style={card}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <Brain size={16} color="var(--accent-purple)" /><h4 style={{ fontSize: '0.9rem', fontWeight: 700 }}>Meterless Engine operations</h4>
          </div>
          {['world_model', ...Object.keys(engines)].map((name) => {
            if (name === 'world_model') {
              const kinds = wm?.observations_by_kind ?? {};
              return (
                <div key={name} style={{ marginBottom: 8, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  <strong style={{ color: 'var(--text-primary)' }}>World Model</strong> <span style={chip(wm?.status === 'connected' ? 'var(--accent-emerald)' : 'var(--accent-rose)')}>{wm?.status ?? 'n/a'}</span>
                  <div style={mono}>{Object.entries(kinds).map(([k, v]) => `${k}×${v}`).join(' • ') || 'no observations'}</div>
                </div>
              );
            }
            const e = engines[name];
            return (
              <div key={name} style={{ marginBottom: 8, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                <strong style={{ color: 'var(--text-primary)' }}>{ENGINE_LABEL[name] ?? name}</strong>{' '}
                <span style={chip(e.bad ? 'var(--accent-rose)' : 'var(--accent-emerald)')}>{e.bad ? `${e.bad} failed` : 'ok'}</span>
                <div style={mono}>{[...e.ops].join(', ')} ({e.calls} call{e.calls === 1 ? '' : 's'})</div>
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ ...card, borderColor: open.length ? 'rgba(244, 63, 94, 0.35)' : 'var(--border-subtle)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
          <ShieldAlert size={16} color="var(--accent-rose)" />
          <h4 style={{ fontSize: '0.9rem', fontWeight: 700 }}>Skeptic review</h4>
          <span style={chip('var(--accent-amber)')}>{result.skeptic?.review_status ?? 'not run'}</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{open.length} open / {objections.length} total objection(s)</span>
        </div>
        {objections.length === 0 && <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>No objections recorded.</div>}
        {objections.map((o, i) => (
          <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 8, opacity: o.open ? 1 : 0.65 }}>
            <span style={chip(o.severity === 'high' ? 'var(--accent-rose)' : 'var(--accent-amber)')}>{o.severity}</span>{' '}
            <strong style={{ color: 'var(--text-primary)' }}>{o.kind}</strong>
            {o.link_id && <> on {o.link_id}</>} (iteration {o.iteration}{o.open ? ', open' : ', superseded'})
            {o.is_missing_evidence_only && <span style={{ color: 'var(--accent-blue)' }}> • missing evidence, not evidence against</span>}
            {!o.grounded && <span style={{ color: 'var(--accent-rose)' }}> • cites unknown IDs: {o.invalid_cited_ids.join(', ')}</span>}
            <div>{o.description}</div>
          </div>
        ))}
      </div>

      {result.memory && (
        <div style={card}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: 6 }}>Persistent memory (H-MEM)</h4>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Prior context retrieved: {result.memory.retrieved.length} (context only — never treated as evidence).{' '}
            Write: {result.memory.write.stored ? 'stored a deterministic-verified lead' : `not stored — ${result.memory.write.reason ?? result.memory.write.error ?? 'below memory floor'}`}
          </div>
        </div>
      )}
    </div>
  );
};
