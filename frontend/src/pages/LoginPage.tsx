import React, { useState } from 'react';
import { Shield, User, BarChart3, Users, Loader2, AlertCircle } from 'lucide-react';
import { api, UserProfile } from '../services/api';

interface LoginPageProps {
  onLogin: (user: UserProfile) => void;
}

const ROLES = [
  {
    key: 'officer',
    label: 'Station Officer',
    description: 'Field OS — Incident reporting, local patrol data',
    icon: <Shield size={28} color="#0284c7" />,
    badge: 'Insp. Rajesh Sharma · PS-SEC17',
    bg: '#eff6ff',
    border: '#bfdbfe',
    accent: '#0284c7',
  },
  {
    key: 'analyst',
    label: 'Crime Analyst',
    description: 'Analyst OS — Cross-station correlations, AI insights',
    icon: <BarChart3 size={28} color="#7c3aed" />,
    badge: 'Dr. Neha Verma · CID Intel',
    bg: '#f5f3ff',
    border: '#ddd6fe',
    accent: '#7c3aed',
  },
  {
    key: 'admin',
    label: 'Police Chief / Admin',
    description: 'Command OS — Full jurisdiction oversight',
    icon: <Users size={28} color="#059669" />,
    badge: 'SSP Kanwardeep Kaur IPS · HQ',
    bg: '#f0fdf4',
    border: '#bbf7d0',
    accent: '#059669',
  },
  {
    key: 'public',
    label: 'Public Citizen',
    description: 'Witness Portal — Anonymous tip submission only',
    icon: <User size={28} color="#64748b" />,
    badge: 'Anonymous · Public Portal',
    bg: '#f8fafc',
    border: '#e2e8f0',
    accent: '#64748b',
  },
];

export const LoginPage: React.FC<LoginPageProps> = ({ onLogin }) => {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (role: string) => {
    setLoading(role);
    setError(null);

    // Rich demo profiles — used instantly if backend is unreachable
    const OFFLINE_PROFILES: Record<string, UserProfile> = {
      officer: {
        user_id: 'usr_sec17_officer',
        name: 'Insp. Rajesh Sharma',
        role: 'officer',
        badge_number: 'CHD-POL-1704',
        station: 'PS-SEC17',
        jurisdiction: 'Chandigarh Police - Sector 17 Central',
        email: 'rajesh.sharma@chandigarhpolice.gov.in',
        token: 'demo_token_officer_sec17',
      },
      analyst: {
        user_id: 'usr_cid_analyst',
        name: 'Dr. Neha Verma',
        role: 'analyst',
        badge_number: 'CID-INTEL-882',
        station: 'CENTRAL_CID',
        jurisdiction: 'Chandigarh Crime Investigation Wing',
        email: 'neha.verma@cid.chd.gov.in',
        token: 'demo_token_analyst_cid',
      },
      admin: {
        user_id: 'usr_ssp_admin',
        name: 'SSP Kanwardeep Kaur, IPS',
        role: 'admin',
        badge_number: 'IPS-CHD-001',
        station: 'POLICE_HQ',
        jurisdiction: 'Chandigarh Police Headquarters (Sector 9)',
        email: 'ssp.chandigarh@nic.in',
        token: 'demo_token_admin_ssp',
      },
      public: {
        user_id: 'usr_citizen_anon',
        name: 'Anonymous Citizen',
        role: 'public',
        badge_number: null,
        station: null,
        jurisdiction: 'Public Witness Portal',
        email: 'anonymous@citizen.portal',
        token: 'demo_token_citizen',
      },
    };

    try {
      // Race: backend call vs 2-second timeout — whichever wins first
      const backendResult = await Promise.race<UserProfile>([
        api.loginUser(role),
        new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('timeout')), 2000)
        ),
      ]);
      onLogin(backendResult);
    } catch {
      // Backend down / timed out → use offline rich profile instantly
      const offlineUser = OFFLINE_PROFILES[role];
      if (offlineUser) {
        onLogin(offlineUser);
      } else {
        setError('Unknown role selected.');
        setLoading(null);
      }
    } finally {
      setLoading(null);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #f8fafc 0%, #e0e7ff 100%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
      }}
    >
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
        <div
          style={{
            width: 64,
            height: 64,
            background: 'linear-gradient(135deg, #4f46e5, #0284c7)',
            borderRadius: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1rem',
            boxShadow: '0 8px 24px rgba(79, 70, 229, 0.3)',
          }}
        >
          <Shield size={32} color="#ffffff" />
        </div>
        <h1
          style={{
            fontSize: '2rem',
            fontWeight: 900,
            color: '#0f172a',
            letterSpacing: '-0.03em',
            marginBottom: '0.35rem',
          }}
        >
          Chandigarh Police
        </h1>
        <p style={{ color: '#4f46e5', fontWeight: 700, fontSize: '0.95rem', letterSpacing: '0.04em' }}>
          CROSS-STATION CRIME INTELLIGENCE PLATFORM
        </p>
        <p style={{ color: '#64748b', fontSize: '0.85rem', marginTop: '0.4rem' }}>
          Select your role to access your personalised OS view
        </p>
      </div>

      {/* Role Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 340px)',
          gap: '1.25rem',
          maxWidth: '720px',
          width: '100%',
        }}
      >
        {ROLES.map((role) => (
          <button
            key={role.key}
            onClick={() => handleLogin(role.key)}
            disabled={loading !== null}
            style={{
              background: role.bg,
              border: `2px solid ${loading === role.key ? role.accent : role.border}`,
              borderRadius: '16px',
              padding: '1.5rem',
              textAlign: 'left',
              cursor: loading !== null ? 'not-allowed' : 'pointer',
              opacity: loading !== null && loading !== role.key ? 0.6 : 1,
              transition: 'all 0.2s ease',
              boxShadow:
                loading === role.key
                  ? `0 0 0 3px ${role.accent}33, 0 4px 16px rgba(0,0,0,0.08)`
                  : '0 2px 8px rgba(0,0,0,0.06)',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
              <div
                style={{
                  width: 48,
                  height: 48,
                  background: '#ffffff',
                  borderRadius: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
                  flexShrink: 0,
                }}
              >
                {loading === role.key ? <Loader2 size={24} color={role.accent} style={{ animation: 'spin 1s linear infinite' }} /> : role.icon}
              </div>
              <div>
                <div style={{ fontWeight: 800, fontSize: '1rem', color: '#0f172a' }}>{role.label}</div>
                <div style={{ fontSize: '0.72rem', color: role.accent, fontWeight: 700, marginTop: '2px' }}>
                  {role.badge}
                </div>
              </div>
            </div>
            <p style={{ fontSize: '0.8rem', color: '#475569', lineHeight: 1.5, margin: 0 }}>
              {role.description}
            </p>
          </button>
        ))}
      </div>

      {error && (
        <div
          style={{
            marginTop: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            color: '#dc2626',
            fontSize: '0.85rem',
            fontWeight: 600,
          }}
        >
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* Footer notice */}
      <p style={{ marginTop: '2rem', fontSize: '0.75rem', color: '#94a3b8', textAlign: 'center', maxWidth: 480 }}>
        Demo credentials — no real passwords required. All data is synthetic for hackathon evaluation.
        Powered by Zetaris NDP · Nightshift AI · Nemotron 3 Skeptic
      </p>
    </div>
  );
};
