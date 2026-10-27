import React, { useEffect, useState } from 'react';
import {
  Layers,
  Search,
  ChevronLeft,
  ChevronRight,
  Eye,
  X,
  FileText,
  Camera,
  Users,
  FlaskConical,
  Shield,
} from 'lucide-react';
import { DataSource, SourceInfo, SourceRecordsResponse } from '../types';
import { api } from '../services/api';

interface SourcesPageProps {
  initialSource?: DataSource;
}

export const SourcesPage: React.FC<SourcesPageProps> = ({ initialSource }) => {
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [activeSource, setActiveSource] = useState<DataSource>(
    initialSource || 'cctv_reports'
  );
  const [recordsData, setRecordsData] = useState<SourceRecordsResponse | null>(null);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(25);
  const [search, setSearch] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedRecord, setSelectedRecord] = useState<Record<string, any> | null>(null);

  // Load source metadata list
  useEffect(() => {
    api.getSources().then((res) => {
      setSources(res.sources);
    }).catch(console.error);
  }, []);

  // Load records for active source
  useEffect(() => {
    setLoading(true);
    api
      .getSourceRecords(activeSource, page, pageSize, search)
      .then((res) => {
        setRecordsData(res);
      })
      .catch(console.error)
      .finally(() => {
        setLoading(false);
      });
  }, [activeSource, page, pageSize, search]);

  const activeSourceInfo = sources.find((s) => s.name === activeSource);

  const getSourceIcon = (src: string) => {
    switch (src) {
      case 'police_incidents':
        return <Shield size={16} />;
      case 'newspaper_reports':
        return <FileText size={16} />;
      case 'witness_reports':
        return <Users size={16} />;
      case 'cctv_reports':
        return <Camera size={16} />;
      case 'forensic_reports':
        return <FlaskConical size={16} />;
      default:
        return <Layers size={16} />;
    }
  };

  const renderTableHeaders = () => {
    switch (activeSource) {
      case 'cctv_reports':
        return (
          <tr>
            <th>CCTV Report ID</th>
            <th>Camera ID</th>
            <th>Location</th>
            <th>Recorded Window</th>
            <th>Movement / Observation</th>
            <th>Confidence</th>
            <th>Quality</th>
            <th>Action</th>
          </tr>
        );
      case 'forensic_reports':
        return (
          <tr>
            <th>Evidence Report ID</th>
            <th>Linked Incident</th>
            <th>Evidence Item</th>
            <th>Type</th>
            <th>Examination Method</th>
            <th>Result Status</th>
            <th>Confidence</th>
            <th>Action</th>
          </tr>
        );
      case 'newspaper_reports':
        return (
          <tr>
            <th>News ID</th>
            <th>Publication</th>
            <th>Published Date</th>
            <th>Headline</th>
            <th>Article Summary</th>
            <th>Action</th>
          </tr>
        );
      case 'witness_reports':
        return (
          <tr>
            <th>Witness Report ID</th>
            <th>Submitted At</th>
            <th>Location</th>
            <th>Statement Summary</th>
            <th>Suspect Description</th>
            <th>Reliability</th>
            <th>Action</th>
          </tr>
        );
      case 'police_incidents':
      default:
        return (
          <tr>
            <th>Incident ID</th>
            <th>Station</th>
            <th>Crime Type</th>
            <th>Location</th>
            <th>Method</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        );
    }
  };

  const renderTableRow = (rec: Record<string, any>, idx: number) => {
    switch (activeSource) {
      case 'cctv_reports':
        return (
          <tr key={idx} onClick={() => setSelectedRecord(rec)} style={{ cursor: 'pointer' }}>
            <td className="mono-cell" style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>
              {rec.cctv_report_id}
            </td>
            <td className="mono-cell">{rec.camera_id}</td>
            <td className="mono-cell" style={{ color: 'var(--text-secondary)' }}>{rec.location_id}</td>
            <td className="mono-cell" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              {rec.recorded_from ? rec.recorded_from.slice(0, 16).replace('T', ' ') : '—'}
            </td>
            <td style={{ maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={rec.movement_description}>
              {rec.movement_description}
            </td>
            <td className="mono-cell">
              {rec.observation_confidence != null ? `${(rec.observation_confidence * 100).toFixed(0)}%` : '—'}
            </td>
            <td>
              <span className="badge" style={{ background: 'rgba(255,255,255,0.08)' }}>
                {rec.image_quality}
              </span>
            </td>
            <td>
              <button className="page-btn" style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem' }}>
                <Eye size={12} />
              </button>
            </td>
          </tr>
        );

      case 'forensic_reports':
        return (
          <tr key={idx} onClick={() => setSelectedRecord(rec)} style={{ cursor: 'pointer' }}>
            <td className="mono-cell" style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>
              {rec.evidence_report_id}
            </td>
            <td className="mono-cell" style={{ color: 'var(--accent-blue)' }}>
              {rec.incident_id || '—'}
            </td>
            <td className="mono-cell">{rec.evidence_item_id}</td>
            <td>
              <span className="badge" style={{ background: 'rgba(56,189,248,0.12)', color: 'var(--accent-blue)' }}>
                {rec.evidence_type}
              </span>
            </td>
            <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={rec.examination_method}>
              {rec.examination_method}
            </td>
            <td>
              <span className="badge" style={{ background: rec.result_status === 'MATCH_CONFIRMED' ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.08)', color: rec.result_status === 'MATCH_CONFIRMED' ? '#34d399' : 'inherit' }}>
                {rec.result_status}
              </span>
            </td>
            <td className="mono-cell">{rec.confidence_level}</td>
            <td>
              <button className="page-btn" style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem' }}>
                <Eye size={12} />
              </button>
            </td>
          </tr>
        );

      case 'newspaper_reports':
        return (
          <tr key={idx} onClick={() => setSelectedRecord(rec)} style={{ cursor: 'pointer' }}>
            <td className="mono-cell" style={{ color: 'var(--accent-amber)', fontWeight: 600 }}>
              {rec.news_id}
            </td>
            <td style={{ fontWeight: 500 }}>{rec.publication_name}</td>
            <td className="mono-cell" style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
              {rec.published_at ? rec.published_at.slice(0, 10) : '—'}
            </td>
            <td style={{ maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 600 }} title={rec.headline}>
              {rec.headline}
            </td>
            <td style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-secondary)' }} title={rec.article_text}>
              {rec.article_text}
            </td>
            <td>
              <button className="page-btn" style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem' }}>
                <Eye size={12} />
              </button>
            </td>
          </tr>
        );

      case 'witness_reports':
        return (
          <tr key={idx} onClick={() => setSelectedRecord(rec)} style={{ cursor: 'pointer' }}>
            <td className="mono-cell" style={{ color: 'var(--accent-purple)', fontWeight: 600 }}>
              {rec.witness_report_id}
            </td>
            <td className="mono-cell" style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
              {rec.submitted_at ? rec.submitted_at.slice(0, 16).replace('T', ' ') : '—'}
            </td>
            <td className="mono-cell">{rec.location_id}</td>
            <td style={{ maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={rec.statement_summary}>
              {rec.statement_summary}
            </td>
            <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-secondary)' }} title={rec.suspect_description}>
              {rec.suspect_description || '—'}
            </td>
            <td>
              <span className="badge" style={{ background: 'rgba(255,255,255,0.08)' }}>
                {rec.witness_reliability}
              </span>
            </td>
            <td>
              <button className="page-btn" style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem' }}>
                <Eye size={12} />
              </button>
            </td>
          </tr>
        );

      case 'police_incidents':
      default:
        return (
          <tr key={idx} onClick={() => setSelectedRecord(rec)} style={{ cursor: 'pointer' }}>
            <td className="mono-cell" style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>
              {rec.incident_id}
            </td>
            <td>
              <span className="badge" style={{ background: 'rgba(255,255,255,0.08)' }}>
                {rec.station_id}
              </span>
            </td>
            <td>{rec.crime_type}</td>
            <td className="mono-cell">{rec.location_id}</td>
            <td style={{ maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-secondary)' }} title={rec.method_description}>
              {rec.method_description}
            </td>
            <td>
              <span className="badge" style={{ background: 'rgba(255,255,255,0.08)' }}>
                {rec.status}
              </span>
            </td>
            <td>
              <button className="page-btn" style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem' }}>
                <Eye size={12} />
              </button>
            </td>
          </tr>
        );
    }
  };

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.35rem', fontWeight: 700 }}>Data Source Explorer</h2>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
          Browse and inspect records across all five registered Zetaris intelligence tables
        </p>
      </div>

      {/* Source Selection Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        {sources.map((src) => {
          const isActive = activeSource === src.name;
          return (
            <button
              key={src.name}
              className={`page-btn ${isActive ? 'active' : ''}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.65rem 1.15rem',
                borderRadius: 'var(--radius-md)',
                background: isActive ? 'linear-gradient(135deg, #1e3a8a, #0284c7)' : 'var(--bg-card)',
                borderColor: isActive ? 'var(--accent-blue)' : 'var(--border-subtle)',
                color: isActive ? '#fff' : 'var(--text-secondary)',
              }}
              onClick={() => {
                setActiveSource(src.name);
                setPage(1);
                setSearch('');
              }}
            >
              {getSourceIcon(src.name)}
              <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{src.label}</span>
              <span
                className="mono-cell"
                style={{
                  fontSize: '0.72rem',
                  padding: '0.1rem 0.4rem',
                  borderRadius: 'var(--radius-full)',
                  background: isActive ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.3)',
                  color: isActive ? '#fff' : 'var(--text-muted)',
                }}
              >
                {src.record_count.toLocaleString()}
              </span>
            </button>
          );
        })}
      </div>

      {/* Active Source Banner & Search */}
      {activeSourceInfo && (
        <div className="filter-bar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{ fontWeight: 700, fontSize: '1rem', color: '#fff' }}>
                {activeSourceInfo.label}
              </span>
              <span className="mono-cell" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                PK: <strong>{activeSourceInfo.primary_key_field}</strong>
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
              {activeSourceInfo.description}
            </p>
          </div>

          <div className="filter-input-group" style={{ maxWidth: '300px' }}>
            <Search size={15} />
            <input
              type="text"
              placeholder={`Search ${activeSourceInfo.label}...`}
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>
        </div>
      )}

      {/* Records Table */}
      <div className="table-wrapper">
        <table className="data-table">
          <thead>{renderTableHeaders()}</thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                  Loading {activeSourceInfo?.label} records...
                </td>
              </tr>
            ) : !recordsData || recordsData.items.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                  No records found in this table matching search criteria.
                </td>
              </tr>
            ) : (
              recordsData.items.map((rec, idx) => renderTableRow(rec, idx))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Bar */}
      {recordsData && (
        <div className="pagination-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span>
              Page <strong>{recordsData.pagination.page}</strong> of <strong>{recordsData.pagination.total_pages}</strong> ({recordsData.pagination.total.toLocaleString()} total)
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Page size:</span>
              <select
                className="filter-select"
                style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
              </select>
            </div>
          </div>

          <div className="pagination-controls">
            <button
              className="page-btn"
              disabled={!recordsData.pagination.has_prev}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft size={16} />
            </button>
            <span className="mono-cell" style={{ padding: '0 0.5rem' }}>
              {recordsData.pagination.page} / {recordsData.pagination.total_pages}
            </span>
            <button
              className="page-btn"
              disabled={!recordsData.pagination.has_next}
              onClick={() => setPage((p) => p + 1)}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Modal / Drawer for Detailed Record Inspection */}
      {selectedRecord && (
        <div className="drawer-backdrop" onClick={() => setSelectedRecord(null)}>
          <div className="drawer-content" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <div>
                <span className="badge" style={{ background: 'rgba(56,189,248,0.15)', color: 'var(--accent-blue)', marginBottom: '0.4rem' }}>
                  {activeSourceInfo?.label} Record
                </span>
                <h3 className="mono-cell" style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>
                  {selectedRecord[activeSourceInfo?.primary_key_field || 'id'] || 'Record Detail'}
                </h3>
              </div>
              <button className="drawer-close-btn" onClick={() => setSelectedRecord(null)}>
                <X size={18} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Full JSON Payload (Normalized Zetaris/NDP Schema):
              </span>
              <pre className="json-view" style={{ maxHeight: '500px' }}>
                {JSON.stringify(selectedRecord, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
