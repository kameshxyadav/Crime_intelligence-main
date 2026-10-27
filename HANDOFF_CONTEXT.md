# 🚔 HANDOFF CONTEXT — Cross-Station Crime Intelligence Platform
**Created:** 2026-10-27 14:46 IST | **Last Updated:** 2026-10-27 15:56 IST | **Status:** Active Handoff — Role-Based Dashboard Isolation

---

## 1. PROJECT OVERVIEW

**What this is:**  
A full-stack crime intelligence platform for the **Open Agent Hackathon 2026 (Track 1: Solving Fragmented Intelligence)**. It simulates how Chandigarh Police unifies crime data across 3 police stations using:
- **Zetaris NDP** — federated data layer (5 JSON data sources unified)
- **Nightshift / Nemotron AI** — AI investigation agent + Nemotron Ultra 550B Skeptic agent that challenges false links
- **Meterless Engines** — World Model + H-MEM conformance engine

**Competitor:** "Nexus" — our system out-benchmarks Nexus with:
- Interactive 3x3 Jurisdictional Correlation & SVG Pulse Map
- Dual Citizen & Officer Tip & Lead Triage Workbench
- Deterministic Skeptic agent challenging coincidences & striking decoys
- Multi-role One OS (Public, Station Officer, Crime Analyst, Police Chief/Admin)

**Project location:**
```
<repo root>/
```

**3 Police Stations (Chandigarh themed):**
| Code | Real Location | Station ID |
|------|--------------|------------|
| NORTH | Industrial Area Phase 1 / Manimajra | PS-INDUSTRIAL |
| CENTRAL | Sector 17 / Sector 22 | PS-SEC17 |
| RIVERSIDE | Sector 40 / Dhanas / Zirakpur | PS-SEC40 |

---

## 2. TECH STACK & PORTS

```
frontend/          → React 18 + TypeScript + Vite (Port 3000)
backend/           → Python 3.11.9 FastAPI + uvicorn (Port 8000)
data/generated/    → 5 JSON data files (10,000 synthetic records)
data/tips_store.json → Persisted citizen tips & officer review states
```

---

## 3. HOW TO RUN

### Terminal 1: Backend (Port 8000)
```powershell
cd "<repo root>/backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
→ API Docs: http://localhost:8000/api/docs

### Terminal 2: Frontend (Port 3000)
```powershell
cd "<repo root>/frontend"
cmd.exe /c "npm run dev"
```
→ App: http://localhost:3000

### Production Build:
```powershell
cd "<repo root>/frontend"
cmd.exe /c "npm run build"
```

### Run Automated Judge CLI:
```powershell
cd "<repo root>"
python run.py --input input_examples/example_1.json
```

---

## 4. ROLE MATRIX & ACCESS RULES

| Role | Demo User | Authorized Tabs | Restricted Tabs | Overview Page Role Card Behavior |
|------|-----------|-----------------|-----------------|----------------------------------|
| **public** | Anonymous Citizen | `overview`, `tip_portal` | `investigation`, `matrix`, `incidents`, `sources`, `zetaris` | Shows Public Safety & Citizen Intake; All internal officer/analyst/chief buttons disabled or routed to tip portal |
| **officer** | Insp. Rajesh Sharma (CHD-POL-1704) | `overview`, `incidents`, `tip_portal` | `investigation`, `matrix`, `sources`, `zetaris` | Shows Field OS & Incident Intake; Analyst & Command buttons show "Requires CID Clearance" |
| **analyst** | Dr. Neha Verma (CID-INTEL-882) | ALL tabs | None | Unrestricted access across all dashboards |
| **admin** | SSP Kanwardeep Kaur, IPS (IPS-CHD-001) | ALL tabs | None | Unrestricted access + Executive Command Oversight banner |

---

## 5. ACTIVE TASK: CROSS-DASHBOARD ISOLATION (USER REQUEST)

**User Issue:**
When logged in as **Public Citizen**, navigating to `overview` previously exposed action buttons ("Explore Investigation Hub", "Launch Officer View", "Open Analyst Hub", "Inspect Command Layer") which allowed citizens to bypass navbar restrictions and enter sensitive officer/analyst dashboards. Furthermore, hash changes in `App.tsx` were unguarded.

**Implemented Fix:**
1. **`App.tsx` Strict Route Guard**:
   - `canAccessTab(role, tab)` helper enforcing the role matrix.
   - `handleTabChange` and `handleHashChange` reject unauthorized tabs and redirect to the user's default permitted tab.
   - `main-content` conditionally renders only authorized tabs; if unauthorized, renders an "Access Restricted / Security Clearance Required" fallback.
2. **`OverviewPage.tsx` Role-Aware Hero & Role Cards**:
   - For `public` role:
     - Hero buttons: "Submit Anonymous Tip" (`tip_portal`) and "Citizen Whistleblower Portal" (`tip_portal`).
     - In the 4 Role Cards: Officer, Analyst, and Command cards show a locked indicator (`🔒 Restricted to Law Enforcement`) with badge indicating clearance required. Only the Public Citizen card has an active action button.
   - For `officer` role:
     - Hero buttons: "Launch Officer Incidents" and "Review Citizen Tips".
     - Analyst Hub and Command Layer show `🔒 Requires CID / HQ Clearance`.
   - For `analyst` & `admin`:
     - Full operational access to all 4 cards.
3. **`Navbar.tsx`**:
   - Displays dynamic label: "Tip Portal" for citizens, "Tip Triage" for officers/analysts/admins.
   - Only displays tabs allowed by `canSee(tab)`.

---

## 6. WHAT HAS BEEN COMPLETED ✅

- **Phase 1 (Judge Path)**: `run.py`, `POST /run`, `SAMPLE_MODE=true`, `metadata.json`, `SPONSOR_TECH.md`.
- **Phase 2 (Agent Reasoning & Skeptic Loop)**: Embedded World Model, Nemotron Ultra 550B skeptic critic, JSONL traces.
- **Phase 3 (Zetaris NDP Data Layer)**: Dual mode adapter (live SQL or local JSON fallback).
- **Phase 4 (UI/UX SaaS Theme)**: Pure white theme, symmetrical 3-column top navbar.
- **Phase 5 (Flagship Features)**: 3x3 Jurisdictional Matrix, SVG pulse map, Chandigarh stations.
- **Phase 6 (Backend Integration & Auth)**: Role-based login (`/api/auth/login`), real tip persistence (`/api/tips/submit`).
- **Phase 7 (UX Polish)**: Live API correlation wiring, tip character counter, admin command banner, dossier export.
- **Phase 8 (Officer Tip Triage & Case Linking)**: Officer review desk, `POST /api/tips/{tip_id}/action`, approve lead, escalate 112, reject decoy, anonymous tracking lookup.
- **Phase 9 (Cross-Dashboard Role Isolation)**: Enforced strict RBAC across `App.tsx`, `OverviewPage.tsx`, and `Navbar.tsx`.

---

## 7. KEY REPOSITORY FILE MAP

```
Crime_intelligence-main/
├── start_backend.bat                          ← One-click backend launcher
├── run.py                                     ← Hackathon evaluation CLI
├── metadata.json                              ← Submission manifest
├── SPONSOR_TECH.md                            ← Technologies utilized proof
├── HANDOFF_CONTEXT.md                         ← THIS FILE
├── PHASES.md                                  ← Roadmap & status
│
├── backend/
│   └── app/
│       ├── main.py                            ← FastAPI registration (29 routes)
│       ├── config.py                          ← Config settings
│       ├── schemas.py                         ← Shared schemas
│       ├── routers/
│       │   ├── auth.py                        ← /api/auth/login, /api/auth/users
│       │   ├── tips.py                        ← /api/tips/submit, /api/tips/{id}/action
│       │   ├── health.py                      ← /api/health, /api/health/zetaris
│       │   ├── incidents.py                   ← /api/incidents
│       │   ├── sources.py                     ← /api/sources
│       │   └── investigations.py              ← /api/investigations/analyze
│       └── services/
│           ├── zetaris_adapter.py             ← Live/JSON twin data access
│           └── meterless_world/               ← World Model & H-MEM engines
│
└── frontend/
    └── src/
        ├── App.tsx                           ← Strict role routing & login gate
        ├── index.css                         ← SaaS theme styles
        ├── components/
        │   └── Navbar.tsx                    ← Symmetrical nav with role-gated tabs
        ├── pages/
        │   ├── LoginPage.tsx                 ← 4-role login selection
        │   ├── OverviewPage.tsx              ← Role-aware One OS with card access locks
        │   ├── InvestigationPage.tsx         ← Multi-agent investigation workbench
        │   ├── CorrelationMapPage.tsx        ← 3x3 matrix & SVG pulse map
        │   ├── PublicTipPortalPage.tsx       ← Dual Citizen Intake & Officer Triage Queue
        │   ├── IncidentsPage.tsx             ← Incident browser
        │   ├── SourcesPage.tsx               ← Zetaris data browser
        │   └── ZetarisStatusPage.tsx         ← Zetaris health monitor
        └── services/
            └── api.ts                        ← Frontend API client
```

---

## 7. PHASE 10: ZETARIS NDP & NVIDIA NEMOTRON INTEGRATION (COMPLETED)

### What was achieved:
1. **Live Environment Configuration (`backend/.env` & `.env`):**
   - Configured `backend/.env` and `.env` with verified Zetaris Docker endpoints (port 8888/3000), organization ID `1`, and live API token.
   - Configured `NIGHTSHIFT_BASE_URL=https://integrate.api.nvidia.com/v1` and pinned target reasoning model `nvidia/nemotron-3-ultra-550b-a55b`.
2. **Live Zetaris Connection Verified:**
   - Docker container `zetaris-api-1` and `zetaris-driver-1` verified active.
   - Direct SQL query `SELECT 1` verified with HTTP 200 via `POST http://localhost:8888/api/v1.0/sql-editor/sqls/run-query` using the configured API token (not recorded here).
   - `GET /api/health/zetaris` returns `status: "connected"`, `configured: True`.
3. **Dual-Mode Resilient Architecture:**
   - Fast namespace inspection (`SHOW TABLES IN lightning.ndp_filestore`) safely checks table availability. If tables are pending file upload in Zetaris NDP File Store, system gracefully serves verified local datasets with zero downtime and zero 500 errors.
4. **NVIDIA Nemotron Inference:**
   - OpenAI-compatible chat completions mapped to `https://integrate.api.nvidia.com/v1`.
   - Instructions provided for active key generation via `build.nvidia.com` `[Generate API Key]`.
5. **Quality Assurance:**
   - 74/74 unit tests passing (`pytest backend/tests/ -q`).
   - Frontend compiles cleanly (`npm run build` in 1.6s, 0 errors).

---

## 8. PHASE 11: JUDGE PATH & DOCKER DEPLOYMENT READINESS (COMPLETED)

### What was achieved:
1. **Root `.env.example` Creation:** Created turnkey configuration template at `<repo root>/.env.example` with exact variable definitions for Zetaris Docker and NVIDIA Nemotron NIM.
2. **True Value Identification & Active Configuration:**
   - Both `<repo root>/.env` and `backend/.env` populated with verified credentials (Zetaris credentials set in the gitignored `.env`, port 8888/3000, and Nemotron Ultra 550B / Lightning 30B).
3. **Turnkey Root `Dockerfile` & `.dockerignore`:**
   - Production Docker container packages Python 3.11 runtime, FastAPI backend, Vite React static frontend (`dist/`), and judge execution CLI.
   - Built successfully via `docker build -t oah-submission .`.
4. **Live Container & Judge Verification:**
   - Container ran with `--env-file .env`: returned `HTTP 200` on `GET /api/health` and `POST /run`.
   - `curl -X POST http://localhost:8000/run -d @input_examples/example_1.json` returned valid cross-station correlation alert in **0.0009s**.
   - Verified 5-step agent audit trace in container logs (`logs/trace-*.jsonl`).
   - Container ran with `-e SAMPLE_MODE=true` (offline, no external network): returned valid correlation report in **0.001s** with zero errors.
5. **Turnkey Judge Documentation:**
   - `README.md` updated with exact clone, build, run, and curl commands.

---

*Last updated: 2026-10-27 17:21 IST*
