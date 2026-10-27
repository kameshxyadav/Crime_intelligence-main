import React, { useEffect, useState } from 'react';
import { Navbar, NavTab } from './components/Navbar';
import { OverviewPage } from './pages/OverviewPage';
import { InvestigationPage } from './pages/InvestigationPage';
import { CorrelationMapPage } from './pages/CorrelationMapPage';
import { PublicTipPortalPage } from './pages/PublicTipPortalPage';
import { IncidentsPage } from './pages/IncidentsPage';
import { SourcesPage } from './pages/SourcesPage';
import { ZetarisStatusPage } from './pages/ZetarisStatusPage';
import { LoginPage } from './pages/LoginPage';
import { DataSource, ZetarisHealthResponse } from './types';
import { api, UserProfile } from './services/api';
import { ShieldAlert, ArrowLeft } from 'lucide-react';

export const ROLE_ALLOWED_TABS: Record<string, NavTab[]> = {
  public: ['overview', 'tip_portal'],
  officer: ['overview', 'incidents', 'tip_portal'],
  analyst: ['overview', 'investigation', 'matrix', 'tip_portal', 'incidents', 'sources', 'zetaris'],
  admin: ['overview', 'investigation', 'matrix', 'tip_portal', 'incidents', 'sources', 'zetaris'],
};

export const isTabAllowedForRole = (role: string | undefined, tab: NavTab): boolean => {
  const allowed = ROLE_ALLOWED_TABS[role || 'public'] || ['overview', 'tip_portal'];
  return allowed.includes(tab);
};

export const App: React.FC = () => {
  // Auth state — null means show login screen
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [activeTab, setActiveTab] = useState<NavTab>('overview');
  const [stationFilter, setStationFilter] = useState<string>('ALL');
  const [selectedSource, setSelectedSource] = useState<DataSource>('cctv_reports');
  const [zetarisHealth, setZetarisHealth] = useState<ZetarisHealthResponse | null>(null);

  // ── Effects (ALL hooks must be before any conditional return) ──
  useEffect(() => {
    if (!currentUser) return; // don't fetch until logged in
    // Race vs 3s timeout so a dead backend never freezes the UI
    Promise.race([
      api.getZetarisHealth(),
      new Promise((_res, reject) =>
        setTimeout(() => reject(new Error('health-timeout')), 3000)
      ),
    ] as [Promise<ZetarisHealthResponse>, Promise<never>])
      .then(setZetarisHealth)
      .catch(() => {
        // Backend offline — set a stub so status pill shows "offline" gracefully
        setZetarisHealth({
          status: 'offline',
          configured: false,
          connected: false,
          latency_ms: null,
          tables_found: [],
          message: 'Backend not reachable (offline demo mode)',
        } as unknown as ZetarisHealthResponse);
      });

    // Listen to hash changes for deep linking with strict role check
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '') as NavTab;
      const validTabs: NavTab[] = [
        'overview',
        'investigation',
        'matrix',
        'tip_portal',
        'incidents',
        'sources',
        'zetaris',
      ];
      if (validTabs.includes(hash)) {
        if (isTabAllowedForRole(currentUser?.role, hash)) {
          setActiveTab(hash);
        } else {
          // Fallback to primary permitted tab
          const allowed = ROLE_ALLOWED_TABS[currentUser?.role || 'public'] || ['overview', 'tip_portal'];
          const fallback = allowed[0] || 'overview';
          setActiveTab(fallback);
          window.location.hash = `#${fallback}`;
        }
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    if (window.location.hash) handleHashChange();

    return () => window.removeEventListener('hashchange', handleHashChange);
  }, [currentUser]); // re-run when user logs in

  // ── Login gate (after all hooks) ──
  if (!currentUser) {
    return (
      <LoginPage
        onLogin={(user) => {
          setCurrentUser(user);
          if (user.role === 'public') {
            setActiveTab('tip_portal');
            window.location.hash = '#tip_portal';
          } else if (user.role === 'officer') {
            setActiveTab('incidents');
            window.location.hash = '#incidents';
          } else {
            setActiveTab('overview');
            window.location.hash = '#overview';
          }
        }}
      />
    );
  }

  const handleSelectStation = (station: string) => {
    if (!isTabAllowedForRole(currentUser?.role, 'incidents')) return;
    setStationFilter(station);
    setActiveTab('incidents');
    window.location.hash = '#incidents';
  };

  const handleNavigateToSources = (sourceName: string) => {
    if (!isTabAllowedForRole(currentUser?.role, 'sources')) return;
    setSelectedSource(sourceName as DataSource);
    setActiveTab('sources');
    window.location.hash = '#sources';
  };

  const handleNavigateToIncidents = () => {
    if (!isTabAllowedForRole(currentUser?.role, 'incidents')) return;
    setStationFilter('ALL');
    setActiveTab('incidents');
    window.location.hash = '#incidents';
  };

  const handleTabChange = (tab: NavTab) => {
    if (!isTabAllowedForRole(currentUser?.role, tab)) {
      const allowed = ROLE_ALLOWED_TABS[currentUser?.role || 'public'] || ['overview', 'tip_portal'];
      const fallback = allowed[0] || 'overview';
      setActiveTab(fallback);
      window.location.hash = `#${fallback}`;
      return;
    }
    setActiveTab(tab);
    window.location.hash = `#${tab}`;
  };

  const userCanAccessCurrentTab = isTabAllowedForRole(currentUser.role, activeTab);

  return (
    <div className="app-container">
      <Navbar
        activeTab={activeTab}
        setActiveTab={handleTabChange}
        zetarisHealth={zetarisHealth}
        currentUser={currentUser}
        onLogout={() => setCurrentUser(null)}
      />

      <main className="main-content">
        {!userCanAccessCurrentTab ? (
          <div style={{ maxWidth: '600px', margin: '4rem auto', textAlign: 'center', background: '#ffffff', padding: '2.5rem', borderRadius: '16px', border: '1px solid #fecaca', boxShadow: '0 4px 12px rgba(239, 68, 68, 0.08)' }}>
            <div style={{ width: 52, height: 52, borderRadius: '50%', background: '#fee2e2', color: '#dc2626', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1rem' }}>
              <ShieldAlert size={28} />
            </div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#0f172a', marginBottom: '0.4rem' }}>
              Access Restricted
            </h2>
            <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: '1.5rem', lineHeight: 1.5 }}>
              Your current profile (<strong>{currentUser.name}</strong> · <code>{currentUser.role.toUpperCase()}</code>) does not have security clearance to view this internal police operating section.
            </p>
            <button
              onClick={() => handleTabChange(currentUser.role === 'public' ? 'tip_portal' : 'overview')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '0.7rem 1.4rem',
                borderRadius: '8px',
                background: '#4f46e5',
                color: '#ffffff',
                fontWeight: 700,
                border: 'none',
                cursor: 'pointer',
              }}
            >
              <ArrowLeft size={16} /> Return to Authorized View
            </button>
          </div>
        ) : (
          <>
            {activeTab === 'overview' && (
              <OverviewPage
                currentUser={currentUser}
                onSelectStation={handleSelectStation}
                onNavigateToSources={handleNavigateToSources}
                onNavigateToIncidents={handleNavigateToIncidents}
                onNavigateToInvestigation={() => handleTabChange('investigation')}
                onNavigateToZetaris={() => handleTabChange('zetaris')}
                onNavigateToTipPortal={() => handleTabChange('tip_portal')}
              />
            )}

            {activeTab === 'investigation' && <InvestigationPage />}

            {activeTab === 'matrix' && <CorrelationMapPage />}

            {activeTab === 'tip_portal' && <PublicTipPortalPage currentUser={currentUser} />}

            {activeTab === 'incidents' && (
              <IncidentsPage initialStation={stationFilter} />
            )}

            {activeTab === 'sources' && (
              <SourcesPage initialSource={selectedSource} />
            )}

            {activeTab === 'zetaris' && <ZetarisStatusPage />}
          </>
        )}
      </main>
    </div>
  );
};

export default App;
