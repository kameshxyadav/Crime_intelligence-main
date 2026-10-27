import React, { useEffect, useState } from 'react';
import { X, AlertTriangle, Link2, GitMerge, FileText, Calendar, MapPin, DollarSign, Tag, CheckCircle2 } from 'lucide-react';
import { IncidentEvidenceResponse, PoliceIncident } from '../types';
import { api } from '../services/api';

interface IncidentDetailModalProps {
  incident: PoliceIncident;
  onClose: () => void;
}

export const IncidentDetailModal: React.FC<IncidentDetailModalProps> = ({
  incident,
  onClose,
}) => {
  const [evidenceData, setEvidenceData] = useState<IncidentEvidenceResponse | null>(null);
  const [loadingEvidence, setLoadingEvidence] = useState<boolean>(true);
  const [expandedRecord, setExpandedRecord] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoadingEvidence(true);
    api
      .getIncidentEvidence(incident.incident_id)
      .then((data) => {
        if (isMounted) setEvidenceData(data);
      })
      .catch((err) => {
        console.error('Failed to load incident evidence:', err);
      })
      .finally(() => {
        if (isMounted) setLoadingEvidence(false);
      });

    return () => {
      isMounted = false;
    };
  }, [incident.incident_id]);

  const getStationBadgeClass = (st: string) => {
    switch (st) {
      case 'NORTH':
        return 'badge-station-north';
      case 'CENTRAL':
        return 'badge-station-central';
      case 'RIVERSIDE':
        return 'badge-station-riverside';
      default:
        return '';
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'OPEN':
        return 'badge-status-open';
      case 'UNDER_INVESTIGATION':
        return 'badge-status-investigation';
      case 'CLOSED':
        return 'badge-status-closed';
      case 'UNRESOLVED':
        return 'badge-status-unresolved';
      default:
        return '';
    }
  };

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="drawer-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.35rem' }}>
              <span className="mono-cell" style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
                {incident.incident_id}
              </span>
              <span className={`badge ${getStationBadgeClass(incident.station_id)}`}>
                {incident.station_id}
              </span>
              <span className={`badge ${getStatusBadgeClass(incident.status)}`}>
                {incident.status.replace('_', ' ')}
              </span>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Crime Type: <strong style={{ color: '#fff' }}>{incident.crime_type}</strong>
            </p>
          </div>
          <button className="drawer-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Basic Metadata Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', background: 'var(--bg-card)', padding: '1.25rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Calendar size={13} /> Reported At
            </span>
            <p className="mono-cell" style={{ marginTop: '0.2rem' }}>
              {incident.reported_at ? new Date(incident.reported_at).toLocaleString() : 'N/A'}
            </p>
          </div>

          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <DollarSign size={13} /> Estimated Loss
            </span>
            <p className="mono-cell" style={{ marginTop: '0.2rem', color: incident.estimated_loss ? 'var(--accent-amber)' : 'inherit' }}>
              {incident.estimated_loss != null ? `$${incident.estimated_loss.toLocaleString()}` : 'N/A'}
            </p>
          </div>

          <div style={{ gridColumn: '1 / -1' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <MapPin size={13} /> Location ({incident.location_id})
            </span>
            <p style={{ marginTop: '0.2rem', fontSize: '0.85rem' }}>
              {incident.location_description}
            </p>
          </div>

          <div style={{ gridColumn: '1 / -1' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <FileText size={13} /> Method of Operation (MO)
            </span>
            <p style={{ marginTop: '0.2rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {incident.method_description}
            </p>
          </div>

          {incident.property_involved && incident.property_involved.length > 0 && (
            <div style={{ gridColumn: '1 / -1' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.35rem' }}>
                <Tag size={13} /> Property Involved
              </span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                {incident.property_involved.map((prop, idx) => (
                  <span key={idx} className="badge" style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--text-primary)' }}>
                    {prop}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Cross-Source Evidence Section */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <GitMerge size={17} color="var(--accent-blue)" />
              Multi-Source Intelligence & Evidence
            </h3>
            {evidenceData && (
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {evidenceData.direct_links.length} Direct • {evidenceData.inferred_links.length} Inferred
              </span>
            )}
          </div>

          {loadingEvidence ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              Searching cross-station data layer for direct and inferred evidence...
            </div>
          ) : !evidenceData ? (
            <div style={{ padding: '1rem', color: 'var(--accent-rose)' }}>
              Failed to load linked evidence.
            </div>
          ) : (
            <div>
              {/* Direct Evidence Section */}
              <div style={{ marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                  <CheckCircle2 size={15} color="var(--accent-emerald)" />
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-emerald)' }}>
                    Direct References ({evidenceData.direct_links.length})
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    Explicit foreign keys registered in incident files
                  </span>
                </div>

                {evidenceData.direct_links.length === 0 ? (
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: '0.5rem 0' }}>
                    No explicit direct source references recorded for this incident.
                  </div>
                ) : (
                  evidenceData.direct_links.map((item, idx) => {
                    const isExpanded = expandedRecord === `direct-${idx}`;
                    return (
                      <div key={idx} className="evidence-card direct">
                        <div className="evidence-header">
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span className="badge badge-direct">DIRECT</span>
                            <span className="mono-cell" style={{ fontWeight: 600, color: '#fff' }}>
                              {item.record_id}
                            </span>
                            <span className="badge" style={{ background: 'rgba(255,255,255,0.08)' }}>
                              {item.source}
                            </span>
                          </div>
                          <button
                            className="page-btn"
                            style={{ fontSize: '0.7rem', padding: '0.2rem 0.5rem' }}
                            onClick={() => setExpandedRecord(isExpanded ? null : `direct-${idx}`)}
                          >
                            {isExpanded ? 'Hide Payload' : 'View Payload'}
                          </button>
                        </div>
                        <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                          Basis: {item.link_basis}
                        </p>
                        {isExpanded && (
                          <pre className="json-view" style={{ marginTop: '0.75rem' }}>
                            {JSON.stringify(item.record, null, 2)}
                          </pre>
                        )}
                      </div>
                    );
                  })
                )}
              </div>

              {/* Inferred Matches Section */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <Link2 size={15} color="var(--accent-purple)" />
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-purple)' }}>
                    Inferred Spatial-Temporal Matches ({evidenceData.inferred_links.length})
                  </span>
                </div>

                <div className="banner warning" style={{ padding: '0.65rem 0.85rem', marginBottom: '0.75rem' }}>
                  <div className="banner-content">
                    <AlertTriangle size={16} />
                    <span style={{ fontSize: '0.74rem' }}>
                      <strong>CAUTION:</strong> Inferred matches are candidate associations based on matching location ({incident.location_id}) and ±48h temporal proximity. They must <em>not</em> be presented as established facts or confirmed evidence.
                    </span>
                  </div>
                </div>

                {evidenceData.inferred_links.length === 0 ? (
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: '0.5rem 0' }}>
                    No spatial-temporal candidate matches found within the ±48h window.
                  </div>
                ) : (
                  evidenceData.inferred_links.map((item, idx) => {
                    const isExpanded = expandedRecord === `inferred-${idx}`;
                    return (
                      <div key={idx} className="evidence-card inferred">
                        <div className="evidence-header">
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span className="badge badge-inferred">INFERRED</span>
                            <span className="mono-cell" style={{ fontWeight: 600, color: '#fff' }}>
                              {item.record_id}
                            </span>
                            <span className="badge" style={{ background: 'rgba(255,255,255,0.08)' }}>
                              {item.source}
                            </span>
                          </div>
                          <button
                            className="page-btn"
                            style={{ fontSize: '0.7rem', padding: '0.2rem 0.5rem' }}
                            onClick={() => setExpandedRecord(isExpanded ? null : `inferred-${idx}`)}
                          >
                            {isExpanded ? 'Hide Payload' : 'View Payload'}
                          </button>
                        </div>
                        <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                          Basis: {item.link_basis}
                        </p>
                        {isExpanded && (
                          <pre className="json-view" style={{ marginTop: '0.75rem' }}>
                            {JSON.stringify(item.record, null, 2)}
                          </pre>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
