import React, { useEffect, useState } from 'react';
import {
  Search,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Eye,
  AlertCircle,
  RotateCcw,
} from 'lucide-react';
import { IncidentFilters, IncidentListResponse, PoliceIncident } from '../types';
import { api } from '../services/api';
import { IncidentDetailModal } from '../components/IncidentDetailModal';

const CRIME_TYPES = [
  'ALL',
  'BURGLARY',
  'ROBBERY',
  'THEFT',
  'VEHICLE_THEFT',
  'CARGO_THEFT',
  'ASSAULT',
  'FRAUD',
  'VANDALISM',
  'NARCOTICS',
  'WEAPONS_VIOLATION',
];

const STATIONS = ['ALL', 'NORTH', 'CENTRAL', 'RIVERSIDE'];
const STATUSES = ['ALL', 'OPEN', 'UNDER_INVESTIGATION', 'CLOSED', 'UNRESOLVED'];

interface IncidentsPageProps {
  initialStation?: string;
}

export const IncidentsPage: React.FC<IncidentsPageProps> = ({ initialStation }) => {
  const [filters, setFilters] = useState<IncidentFilters>({
    page: 1,
    pageSize: 25,
    search: '',
    station: initialStation || 'ALL',
    crimeType: 'ALL',
    status: 'ALL',
    sortBy: 'reported_at',
    sortDesc: true,
  });

  const [data, setData] = useState<IncidentListResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIncident, setSelectedIncident] = useState<PoliceIncident | null>(null);

  const loadData = () => {
    setLoading(true);
    api
      .getIncidents(filters)
      .then((res) => {
        setData(res);
        setError(null);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load incidents');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, [
    filters.page,
    filters.pageSize,
    filters.station,
    filters.crimeType,
    filters.status,
    filters.sortBy,
    filters.sortDesc,
  ]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFilters((prev) => ({ ...prev, page: 1 }));
    loadData();
  };

  const handleResetFilters = () => {
    setFilters({
      page: 1,
      pageSize: 25,
      search: '',
      station: 'ALL',
      crimeType: 'ALL',
      status: 'ALL',
      sortBy: 'reported_at',
      sortDesc: true,
    });
  };

  const getStationBadge = (st: string) => {
    if (st === 'NORTH') return 'badge-station-north';
    if (st === 'CENTRAL') return 'badge-station-central';
    return 'badge-station-riverside';
  };

  const getStatusBadge = (status: string) => {
    if (status === 'OPEN') return 'badge-status-open';
    if (status === 'UNDER_INVESTIGATION') return 'badge-status-investigation';
    if (status === 'CLOSED') return 'badge-status-closed';
    return 'badge-status-unresolved';
  };

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700 }}>Police Incidents Intelligence</h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            Search, filter, and inspect incidents across North, Central, and Riverside stations
          </p>
        </div>

        {data && (
          <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
            Showing <strong>{data.items.length}</strong> of <strong>{data.pagination.total.toLocaleString()}</strong> records
          </div>
        )}
      </div>

      {/* Filter Bar */}
      <div className="filter-bar">
        {/* Search Input */}
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', flex: '2', minWidth: '240px' }}>
          <div className="filter-input-group">
            <Search size={16} />
            <input
              type="text"
              placeholder="Search ID, location, MO..."
              value={filters.search || ''}
              onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
            />
          </div>
        </form>

        {/* Station filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <select
            className="filter-select"
            value={filters.station}
            onChange={(e) => setFilters((prev) => ({ ...prev, station: e.target.value, page: 1 }))}
          >
            {STATIONS.map((s) => (
              <option key={s} value={s}>
                {s === 'ALL' ? 'All Stations' : `${s} Station`}
              </option>
            ))}
          </select>
        </div>

        {/* Crime Type filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <select
            className="filter-select"
            value={filters.crimeType}
            onChange={(e) => setFilters((prev) => ({ ...prev, crimeType: e.target.value, page: 1 }))}
          >
            {CRIME_TYPES.map((c) => (
              <option key={c} value={c}>
                {c === 'ALL' ? 'All Crime Types' : c.replace('_', ' ')}
              </option>
            ))}
          </select>
        </div>

        {/* Status filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <select
            className="filter-select"
            value={filters.status}
            onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value, page: 1 }))}
          >
            {STATUSES.map((st) => (
              <option key={st} value={st}>
                {st === 'ALL' ? 'All Statuses' : st.replace('_', ' ')}
              </option>
            ))}
          </select>
        </div>

        {/* Sort By */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <select
            className="filter-select"
            value={filters.sortBy}
            onChange={(e) => setFilters((prev) => ({ ...prev, sortBy: e.target.value }))}
          >
            <option value="reported_at">Sort: Reported Date</option>
            <option value="occurred_from">Sort: Occurred Date</option>
            <option value="estimated_loss">Sort: Estimated Loss</option>
            <option value="crime_type">Sort: Crime Type</option>
            <option value="status">Sort: Status</option>
          </select>
          <button
            className="page-btn"
            title={filters.sortDesc ? 'Descending (Z-A / Newest)' : 'Ascending (A-Z / Oldest)'}
            onClick={() => setFilters((prev) => ({ ...prev, sortDesc: !prev.sortDesc }))}
          >
            <ArrowUpDown size={14} />
          </button>
        </div>

        {/* Reset button */}
        <button
          className="page-btn"
          onClick={handleResetFilters}
          title="Reset all filters"
          style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}
        >
          <RotateCcw size={13} />
          Reset
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="banner warning" style={{ marginBottom: '1.5rem' }}>
          <div className="banner-content">
            <AlertCircle size={18} />
            <span>Error fetching incidents: {error}</span>
          </div>
        </div>
      )}

      {/* Incidents Table */}
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Incident ID</th>
              <th>Station</th>
              <th>Crime Type</th>
              <th>Location</th>
              <th>Method (MO)</th>
              <th>Est. Loss</th>
              <th>Reported Date</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                  Loading incident records from data layer...
                </td>
              </tr>
            ) : !data || data.items.length === 0 ? (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                  No police incident records found matching current filters.
                </td>
              </tr>
            ) : (
              data.items.map((inc) => (
                <tr
                  key={inc.incident_id}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setSelectedIncident(inc)}
                >
                  <td className="mono-cell" style={{ fontWeight: 600, color: 'var(--accent-blue)' }}>
                    {inc.incident_id}
                  </td>
                  <td>
                    <span className={`badge ${getStationBadge(inc.station_id)}`}>
                      {inc.station_id}
                    </span>
                  </td>
                  <td style={{ fontWeight: 500 }}>
                    {inc.crime_type.replace('_', ' ')}
                  </td>
                  <td style={{ maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={inc.location_description}>
                    <span className="mono-cell" style={{ color: 'var(--text-muted)', marginRight: '0.35rem' }}>[{inc.location_id}]</span>
                    {inc.location_description}
                  </td>
                  <td style={{ maxWidth: '220px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-secondary)' }} title={inc.method_description}>
                    {inc.method_description}
                  </td>
                  <td className="mono-cell">
                    {inc.estimated_loss != null ? `$${inc.estimated_loss.toLocaleString()}` : '—'}
                  </td>
                  <td className="mono-cell" style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                    {inc.reported_at ? inc.reported_at.slice(0, 10) : '—'}
                  </td>
                  <td>
                    <span className={`badge ${getStatusBadge(inc.status)}`}>
                      {inc.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td>
                    <button
                      className="page-btn"
                      style={{ padding: '0.25rem 0.6rem', display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.72rem' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedIncident(inc);
                      }}
                    >
                      <Eye size={12} />
                      Inspect
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      {data && (
        <div className="pagination-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span>
              Page <strong>{data.pagination.page}</strong> of <strong>{data.pagination.total_pages}</strong>
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Rows per page:</span>
              <select
                className="filter-select"
                style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                value={filters.pageSize}
                onChange={(e) => setFilters((prev) => ({ ...prev, pageSize: Number(e.target.value), page: 1 }))}
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>
          </div>

          <div className="pagination-controls">
            <button
              className="page-btn"
              disabled={!data.pagination.has_prev}
              onClick={() => setFilters((prev) => ({ ...prev, page: Math.max(1, prev.page - 1) }))}
            >
              <ChevronLeft size={16} />
            </button>
            <span className="mono-cell" style={{ padding: '0 0.5rem' }}>
              {data.pagination.page} / {data.pagination.total_pages}
            </span>
            <button
              className="page-btn"
              disabled={!data.pagination.has_next}
              onClick={() => setFilters((prev) => ({ ...prev, page: prev.page + 1 }))}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Modal Drawer when an incident is selected */}
      {selectedIncident && (
        <IncidentDetailModal
          incident={selectedIncident}
          onClose={() => setSelectedIncident(null)}
        />
      )}
    </div>
  );
};
