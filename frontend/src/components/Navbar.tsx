import React from 'react';
import { Shield, Database, LayoutDashboard, FileSearch, Layers, BrainCircuit, GitMerge, ShieldCheck, LogOut } from 'lucide-react';
import { ZetarisHealthResponse } from '../types';
import { UserProfile } from '../services/api';

export type NavTab = 'overview' | 'investigation' | 'matrix' | 'tip_portal' | 'incidents' | 'sources' | 'zetaris';

interface NavbarProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  zetarisHealth: ZetarisHealthResponse | null;
  currentUser?: UserProfile | null;
  onLogout?: () => void;
}

const ROLE_COLORS: Record<string, string> = {
  officer: '#0284c7',
  analyst: '#7c3aed',
  admin: '#059669',
  public: '#64748b',
};

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  zetarisHealth,
  currentUser,
  onLogout,
}) => {
  const isZetarisLive = zetarisHealth?.status === 'connected';
  const roleColor = currentUser ? (ROLE_COLORS[currentUser.role] ?? '#4f46e5') : '#4f46e5';
  const role = currentUser?.role ?? 'analyst';

  // Role-based tab visibility:
  // - public  → tip_portal only (+ overview)
  // - officer → overview, incidents, tip_portal
  // - analyst → everything
  // - admin   → everything
  const canSee = (tab: NavTab): boolean => {
    if (role === 'admin' || role === 'analyst') return true;
    if (role === 'officer') return ['overview', 'incidents', 'tip_portal'].includes(tab);
    if (role === 'public') return ['overview', 'tip_portal'].includes(tab);
    return true;
  };

  return (
    <header className="top-nav">
      {/* 1. Left: Brand Section */}
      <div className="brand-section">
        <div className="brand-logo">
          <Shield size={20} />
        </div>
        <div className="brand-title-group">
          <h1>CROSS-STATION INTEL</h1>
          <span className="brand-subtitle">
            Sec 17 • Sec 22 • Industrial Phase 1
          </span>
        </div>
      </div>

      {/* 2. Center: Perfectly Centered Pill Tabs */}
      <nav className="nav-links">
        {canSee('overview') && (
          <button
            className={`nav-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <LayoutDashboard size={14} />
            Overview
          </button>
        )}
        {canSee('investigation') && (
          <button
            className={`nav-btn ${activeTab === 'investigation' ? 'active' : ''}`}
            onClick={() => setActiveTab('investigation')}
          >
            <BrainCircuit size={14} />
            Investigation Hub
          </button>
        )}
        {canSee('matrix') && (
          <button
            className={`nav-btn ${activeTab === 'matrix' ? 'active' : ''}`}
            onClick={() => setActiveTab('matrix')}
          >
            <GitMerge size={14} />
            Correlation &amp; Map
          </button>
        )}
        {canSee('tip_portal') && (
          <button
            className={`nav-btn ${activeTab === 'tip_portal' ? 'active' : ''}`}
            onClick={() => setActiveTab('tip_portal')}
          >
            <ShieldCheck size={14} />
            {currentUser && ['officer', 'analyst', 'admin'].includes(currentUser.role)
              ? 'Tip Triage'
              : 'Tip Portal'}
          </button>
        )}
        {canSee('incidents') && (
          <button
            className={`nav-btn ${activeTab === 'incidents' ? 'active' : ''}`}
            onClick={() => setActiveTab('incidents')}
          >
            <FileSearch size={14} />
            Incidents
          </button>
        )}
        {canSee('sources') && (
          <button
            className={`nav-btn ${activeTab === 'sources' ? 'active' : ''}`}
            onClick={() => setActiveTab('sources')}
          >
            <Layers size={14} />
            Sources
          </button>
        )}
        {canSee('zetaris') && (
          <button
            className={`nav-btn ${activeTab === 'zetaris' ? 'active' : ''}`}
            onClick={() => setActiveTab('zetaris')}
          >
            <Database size={14} />
            Zetaris
          </button>
        )}
      </nav>

      {/* 3. Right: User Badge + Status */}
      <div className="header-status" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <div
          className={`status-pill ${isZetarisLive ? 'connected' : 'not_configured'}`}
          title={zetarisHealth?.message || 'Checking data layer status...'}
        >
          <div className="status-dot" />
          <span>
            {isZetarisLive ? 'ZETARIS: LIVE' : 'DATA: LOCAL FALLBACK'}
          </span>
        </div>

        {currentUser && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div
              style={{
                background: `${roleColor}18`,
                border: `1px solid ${roleColor}44`,
                borderRadius: '8px',
                padding: '4px 10px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.72rem',
                fontWeight: 700,
                color: roleColor,
                maxWidth: 160,
                overflow: 'hidden',
                whiteSpace: 'nowrap',
                textOverflow: 'ellipsis',
              }}
              title={`${currentUser.name} · ${currentUser.jurisdiction}`}
            >
              <div style={{ width: 7, height: 7, borderRadius: '50%', background: roleColor, flexShrink: 0 }} />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {currentUser.name.split(' ').slice(-2).join(' ')}
              </span>
            </div>
            {onLogout && (
              <button
                onClick={onLogout}
                title="Logout"
                style={{
                  background: 'none',
                  border: '1px solid #e2e8f0',
                  borderRadius: '7px',
                  padding: '5px 7px',
                  cursor: 'pointer',
                  color: '#94a3b8',
                  display: 'flex',
                  alignItems: 'center',
                  transition: 'all 0.15s',
                }}
              >
                <LogOut size={14} />
              </button>
            )}
          </div>
        )}
      </div>
    </header>
  );
};
