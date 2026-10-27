# Cross-Station Crime Intelligence: Multi-Station Investigation System

> **Open Agent Hackathon 2026** — *Track 1: Solving Fragmented Intelligence*  
> **Team:** Cross-Station AI

This repository contains the full-stack intelligence platform, synthetic data generation pipeline, and multi-agent reasoning engine for the **Cross-Station Crime Intelligence** system. It unifies **10,000 multi-source intelligence records across five datasets** (police incidents, forensics, CCTV, witness statements, and media reports) across three jurisdictions (North, Central, and Riverside stations in Chandigarh Police theme).

---

## ⚡ Test It Like a Judge Would (Turnkey Evaluation)

Before submission, verify on any machine with Docker installed:

```bash
# 1. Clone repository & configure
git clone <your-repo-url>
cd cross-station-crime-intelligence
cp .env.example .env     # fill in Zetaris / Nemotron credentials if evaluating live

# 2. Build submission container
docker build -t oah-submission .

# 3. Run container (Live Mode with credentials)
docker run --rm -d --name oah-submission -p 8000:8000 --env-file .env oah-submission

# 4. Execute Judge Evaluation Endpoint
#    example_1.json sets sample_mode:true (pre-built replay). For a LIVE multi-agent run (3-6 min, needs Zetaris +
#    Nightshift configured in .env) send sample_mode:false:
#      curl -X POST http://localhost:8000/run -H "Content-Type: application/json" \
#        -d '{"sample_mode":false,"query":"Are INC-NORTH-0042 and INC-CEN-0118 related?"}'
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d @input_examples/example_1.json

# 5. Inspect container logs and agent receipts
docker logs oah-submission
docker exec oah-submission sh -c 'cat logs/trace-*.jsonl'

# 6. Stop container
docker stop oah-submission
```

### 🛡️ Standalone Zero-Credential Offline Evaluation (Sample Mode)
To test like a judge on an offline machine without Zetaris or NVIDIA network access:
```bash
# Replays a pre-built scenario (no agent, model, Zetaris query or engine runs; the response and trace say so):
docker run --rm -d --name oah-sample -p 8000:8000 -e SAMPLE_MODE=true oah-submission

curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d @input_examples/example_1.json

docker logs oah-sample
docker stop oah-sample
```

### 💻 Host Quick Start (Without Docker)
```bash
# 1. Backend API (Terminal 1)
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 2. Frontend One OS UI (Terminal 2)
cd ../frontend
npm install
npm run dev

# 3. Host CLI Judge Evaluation (Terminal 3)
cd ..
python run.py --input input_examples/example_1.json
```

---

## 1. Project Directory Structure

```text
cross-station-crime-intelligence/
├── data/
│   ├── generated/
│   │   ├── police_incidents.json      # 3,000 records
│   │   ├── newspaper_reports.json     # 1,500 records
│   │   ├── witness_reports.json       # 2,000 records
│   │   ├── cctv_reports.json          # 2,000 records
│   │   └── forensic_reports.json      # 1,500 records
│   └── evaluation/
│       └── ground_truth.json          # Offline planted relationships benchmark
├── scripts/
│   └── generate_synthetic_data.py     # Deterministic data generation script
├── tests/
│   └── test_synthetic_data.py         # Pytest verification and schema validation
├── requirements.txt
└── README.md
```

---

## 2. Dataset Overview & Quotas

All datasets are valid UTF-8 JSON arrays of objects with standard ISO 8601 UTC timestamps ending in `Z`. Unknown scalars are represented as `null` and absent lists as empty arrays `[]`.

| Dataset File | Target Records | Primary Entity / Focus |
| :--- | :--- | :--- |
| `data/generated/police_incidents.json` | **3,000** | Formal police incident reports across 3 stations |
| `data/generated/newspaper_reports.json` | **1,500** | Public press coverage, investigative journalism, and police blotters |
| `data/generated/witness_reports.json` | **2,000** | Citizen and pedestrian observations, tipoffs, and vehicle sightings |
| `data/generated/cctv_reports.json` | **2,000** | Automated surveillance feeds, optical sightings, and motion analysis |
| `data/generated/forensic_reports.json` | **1,500** | Physical, biological, chemical, and digital evidence lab analyses |
| **Total primary source records** | **10,000** | **Exact Hackathon Target** |
| `data/evaluation/ground_truth.json` | **8 Scenarios** | **Offline evaluation benchmark (never exposed to Zetaris tables)** |

---

## 3. Schemas

### 3.1 Police Incidents (`police_incidents.json`)
* **`incident_id`** *(string)*: Unique identifier (e.g. `INC-NORTH-0042`, `INC-CEN-0118`).
* **`station_id`** *(string)*: Station jurisdiction (`NORTH`, `CENTRAL`, or `RIVERSIDE`).
* **`reported_at`** *(string)*: ISO 8601 UTC timestamp (`YYYY-MM-DDTHH:MM:SSZ`).
* **`occurred_from`** *(string)*: Start of occurrence window (`YYYY-MM-DDTHH:MM:SSZ`).
* **`occurred_to`** *(string | null)*: End of occurrence window, or `null` if instantaneous or unknown.
* **`crime_type`** *(string)*: Offense category (`BURGLARY`, `VEHICLE_THEFT`, `ROBBERY`, `SHOPLIFTING`, `VANDALISM`, `FRAUD`, `CARGO_THEFT`, etc.).
* **`location_id`** *(string)*: Standardized fictional location code (e.g. `LOC-NORTH-01`).
* **`location_description`** *(string)*: Human-readable location description.
* **`method_description`** *(string)*: Narrative modus operandi description.
* **`property_involved`** *(list[string])*: Stolen, damaged, or involved property items.
* **`estimated_loss`** *(float | null)*: Monetary loss valuation in USD, or `null`.
* **`status`** *(string)*: Case status (`OPEN`, `UNDER_INVESTIGATION`, `CLOSED`, `UNRESOLVED`).
* **`source_reference_ids`** *(list[string])*: Explicitly indexed reference IDs or `[]`.
* **`data_quality`** *(string)*: Data fidelity rating (`HIGH`, `MEDIUM`, `LOW`).

### 3.2 Newspaper Reports (`newspaper_reports.json`)
* **`news_id`** *(string)*: Unique news identifier (e.g. `NEWS-0064`).
* **`publication_name`** *(string)*: Press outlet (e.g. `Metro Daily Gazette`, `Central City Chronicle`).
* **`published_at`** *(string)*: ISO 8601 UTC timestamp of publication.
* **`headline`** *(string)*: Article headline.
* **`article_text`** *(string)*: Full news report body.
* **`mentioned_date_from`** *(string | null)*: Date range referenced in article.
* **`mentioned_date_to`** *(string | null)*: Date range referenced in article.
* **`mentioned_location_ids`** *(list[string])*: Location IDs referenced in coverage.
* **`crime_labels`** *(list[string])*: Editorial crime classification tags.
* **`mentioned_property`** *(list[string])*: Property items discussed in the article.
* **`related_incident_ids`** *(list[string])*: Explicit incident references if known to the press.
* **`source_reliability`** *(string)*: Journalist credibility score (`HIGH`, `MEDIUM`, `LOW`, `UNVERIFIED`).
* **`data_quality`** *(string)*: Metadata fidelity rating (`HIGH`, `MEDIUM`, `LOW`).

### 3.3 Witness Reports (`witness_reports.json`)
* **`witness_report_id`** *(string)*: Unique witness observation ID (e.g. `WIT-0105`).
* **`submitted_at`** *(string)*: ISO 8601 UTC timestamp of statement intake.
* **`observed_from`** *(string)*: Start of observation timeframe.
* **`observed_to`** *(string | null)*: End of observation timeframe.
* **`location_id`** *(string)*: Location ID where witness made the sighting.
* **`observation_text`** *(string)*: Verbatim witness account.
* **`observed_entities`** *(list[string])*: Extracted descriptions of persons, bags, or items.
* **`vehicle_description`** *(string | null)*: Descriptive vehicle notes, or `null`.
* **`direction_of_travel`** *(string | null)*: Fleeing direction or trajectory, or `null`.
* **`confidence_level`** *(string)*: Witness certainty (`HIGH`, `MEDIUM`, `LOW`, `UNCERTAIN`).
* **`related_incident_ids`** *(list[string])*: Explicitly linked incident IDs, or `[]`.
* **`contradiction_flags`** *(list[string])*: Identified discrepancies (e.g. `["disputes_suspect_count"]`).
* **`data_quality`** *(string)*: Metadata completeness rating (`HIGH`, `MEDIUM`, `LOW`).

### 3.4 CCTV Reports (`cctv_reports.json`)
* **`cctv_report_id`** *(string)*: Unique surveillance clip ID (e.g. `CCTV-0112`).
* **`camera_id`** *(string)*: Camera infrastructure ID (e.g. `CAM-NORTH-01-01`).
* **`location_id`** *(string)*: Monitored location code.
* **`recorded_from`** *(string)*: Start timestamp of recording window.
* **`recorded_to`** *(string | null)*: End timestamp of recording window.
* **`observed_entities`** *(list[string])*: Computer vision / operator entity tags.
* **`vehicle_description`** *(string | null)*: Make, model, or body style description, or `null`.
* **`vehicle_color`** *(string | null)*: Vehicle exterior paint color, or `null`.
* **`partial_plate`** *(string | null)*: Legible plate characters (e.g. `7XK***`), or `null`.
* **`movement_description`** *(string)*: Trajectory and behavior summary.
* **`image_quality`** *(string)*: Optical fidelity (`CLEAR`, `MODERATE`, `DEGRADED`, `NIGHT_IR_LOW_RES`, `PARTIAL_GLARE`, `POOR`).
* **`observation_confidence`** *(float)*: Numeric certainty score between `0.0` and `1.0`.
* **`related_incident_ids`** *(list[string])*: Explicit incident references, or `[]`.
* **`data_quality`** *(string)*: Metadata quality (`HIGH`, `MEDIUM`, `LOW`).

### 3.5 Forensic Reports (`forensic_reports.json`)
* **`evidence_report_id`** *(string)*: Unique laboratory report ID (e.g. `FOR-0089`).
* **`incident_id`** *(string | null)*: Police incident ID if item was logged from a scene, or `null`.
* **`evidence_item_id`** *(string)*: Physical evidence barcode ID (e.g. `EVD-2025-0089`).
* **`collected_at`** *(string)*: ISO 8601 UTC timestamp of evidence collection.
* **`location_id`** *(string)*: Recovery location code.
* **`evidence_type`** *(string)*: Discipline (`TOOLMARK`, `DNA`, `FINGERPRINT`, `BALLISTICS`, `DIGITAL_FOOTPRINT`, `CHEMICAL_RESIDUE`, `TIRE_IMPRESSION`, `FIBER`).
* **`description`** *(string)*: Physical description of sample or substrate.
* **`examination_method`** *(string)*: Analytical technique (`COMPARISON_MICROSCOPY`, `STR_PROFILING`, `AFIS_LATENT_SCAN`, `GC_MS`, `LOG_AND_SIGNAL_ANALYSIS`, `TREAD_PHOTOGRAMMETRY`).
* **`result_summary`** *(string)*: Examiner's technical conclusions.
* **`result_status`** *(string)*: Outcome status (`MATCH_CONFIRMED`, `INCONCLUSIVE`, `EXCLUSION`, `PENDING_REFERENCE`, `PARTIAL_MATCH`).
* **`confidence_level`** *(string)*: Scientific certainty (`HIGH`, `MEDIUM`, `LOW`, `INCONCLUSIVE`).
* **`compared_evidence_ids`** *(list[string])*: Cross-referenced evidence item barcodes.
* **`limitations`** *(string | null)*: Known methodological constraints or sample degradation, or `null`.
* **`data_quality`** *(string)*: Quality grade (`HIGH`, `MEDIUM`, `LOW`).

---

## 4. Synthetic World Design

The synthetic environment models three fictional police precincts within a single metropolitan county:

1. **`NORTH` Precinct**:
   * Northern industrial parks, distribution terminals, and tech corridors (`LOC-NORTH-01` to `LOC-NORTH-20`).
   * Characterized by logistics parks, server facilities, and suburban residential estates.
2. **`CENTRAL` Precinct**:
   * Dense commercial downtown core, financial high-rises, transit terminals, and luxury shopping arcades (`LOC-CEN-01` to `LOC-CEN-20`).
   * High volume of pedestrian traffic, bank facilities, and municipal buildings.
3. **`RIVERSIDE` Precinct**:
   * Maritime docks, cargo shipping yards, marine slips, commuter rail terminals, and container freight storage (`LOC-RIV-01` to `LOC-RIV-20`).
   * Intermodal logistics transit points connecting rail, marine, and road freight.

* **Privacy & Ethical Safeguards**: All locations, company names, camera IDs, citizen accounts, and vehicle registrations are 100% fictional. No real personal identifiable information (PII) or real police records are used.

---

## 5. Agent Reasoning Challenges

The dataset is purposefully curated with complex multi-table reasoning features designed to challenge and evaluate autonomous AI agents:

* **Planted Multi-Station Crime Rings**:
  * *Crowbar Commercial Safe Crackers* (`REL-SERIES-001`): Series spanning `NORTH` and `CENTRAL` linked by 36mm chisel-tip toolmark striations and a dark grey minivan with a dented tailgate (`7XK***`).
  * *Commuter Rail Catalytic Converter Syndicate* (`REL-SERIES-002`): Rapid sub-90-second thefts spanning `CENTRAL` and `RIVERSIDE` linked by GC-MS titanium carbonitride blade metallurgy.
  * *Keyless Luxury SUV Relay Ring* (`REL-SERIES-003`): Push-to-start relay attacks spanning `NORTH` and `RIVERSIDE` linked by RF signal injection telemetry logs.
  * *Impostor Utility Inspector Scam* (`REL-SERIES-004`): Distraction burglaries spanning `CENTRAL` and `NORTH` linked by latent palm prints and a white utility van with roof ladder rack.
  * *Pharmaceutical Cold-Storage Diversion* (`REL-SERIES-007`): Cargo fraud spanning `RIVERSIDE` and `CENTRAL` linked by compromised digital manifest cryptographic signatures.
* **Contradictory Eyewitness Accounts**: Discrepancies in perceived suspect clothing colors (red jacket vs dark hoodie) and vehicle body styles (minivan vs SUV).
* **Discoverable vs. Explicit Links**: Many connected records have `related_incident_ids: []`, requiring the agent to deduce links from spatial-temporal proximity, vehicle partial plates, and forensic comparison IDs (`compared_evidence_ids`).
* **Degraded CCTV Feeds & Inconclusive Forensics**: Low-resolution night infrared cameras, headlights glare, partial latent fingerprints, and inconclusive lab results.
* **Intentional Distractors & Exclusions**:
  * `REL-DISTRACTOR-006`: A legitimate commercial plumbing van (`Apex Municipal Plumbing`) that was falsely reported by an anxious neighbor, forensically excluded via tire tread analysis.
  * `REL-DISTRACTOR-008`: An amateur juvenile smash-and-grab using a cinder block that occurred in the same precinct as the professional crowbar syndicate, definitively excluded via DNA.
* **Realistic Needle-in-a-Haystack Noise**: The majority of the 10,000 records comprise diverse background incidents, routine CCTV recordings, and unrelated forensic tests.

---

## 6. Offline Ground Truth Benchmark

Planted relationships are documented in `data/evaluation/ground_truth.json`.
This file is strictly for **offline evaluation** to measure precision, recall, and reasoning fidelity:
* It is **never** registered as a Zetaris table.
* It is **never** exposed to agent runtime APIs or query endpoints.
* Each scenario contains: `relationship_id`, `title`, `stations_involved`, `incident_ids`, `source_record_ids`, `why_related`, `supporting_evidence`, `contradictions_and_limitations`, and `confidence_label`.

---

## 7. How to Run & Validate

### 7.1 Setup Environment

```bash
# Backend dependencies
pip install -r backend/requirements.txt

# Frontend dependencies
cd frontend && npm install && cd ..
```

### 7.2 Run Automated Test Suites

```bash
# Run synthetic data generator tests (13 tests)
pytest -v tests/test_synthetic_data.py

# Run backend API and integration tests (unit + mocked + local-engine; live tests are skipped unless RUN_LIVE_TESTS=1)
pytest -v backend/tests/
```

### 7.3 Start the Application

```bash
# Terminal 1: Launch FastAPI Backend (runs on port 8000)
cd backend
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Launch React / Vite Dashboard (runs on port 5173)
cd frontend
npm run dev
```

Visit `http://localhost:5173` in your browser.

---

## 8. Backend API & Zetaris Integration Layer

The Python backend is built with **FastAPI** and **Pydantic**, providing typed response schemas and strict security boundaries.

### 8.1 Implemented Endpoints

| Category | Endpoint | Description |
| :--- | :--- | :--- |
| **Health** | `GET /api/health` | Application status, API version, and environment |
| **Health** | `GET /api/health/zetaris` | Zetaris data layer probe (`connected`, `not_configured`, `connection_failed`) |
| **Dashboard** | `GET /api/dashboard/summary` | Aggregated metrics: incident counts, station distributions, crime types, status, sources, timeline |
| **Incidents** | `GET /api/incidents` | Multi-filter pagination, search, station, crime type, status, date range, sorting |
| **Incidents** | `GET /api/incidents/{id}` | Detailed police incident record |
| **Evidence** | `GET /api/incidents/{id}/evidence` | Explicit cross-source evidence links (direct foreign keys vs. inferred spatio-temporal matches) |
| **Sources** | `GET /api/sources` | Metadata, record counts, and primary keys for all 5 registered tables |
| **Sources** | `GET /api/sources/{source}/records` | Paginated exploration of source-specific schemas |
| **Sources** | `GET /api/sources/{source}/records/{id}` | Individual source record payload |

### 8.2 Zetaris NDP Integration Adapter

The integration layer (`backend/app/services/zetaris_adapter.py`) isolates all Zetaris-specific connectivity:
- **Connection Status**: Transparently reports whether Zetaris is connected. When unconfigured, reports `NOT CONFIGURED` with active mode `local_fallback`.
- **Query Safety**: Search terms and IDs are sanitized (allow-list of characters) before being interpolated into SQL; all SQL is read-only `SELECT`. (They are not bound parameters.)
- **Fail-Safe Policy**: Never silently substitutes synthetic data when live Zetaris queries fail; explicitly tags responses with `data_mode`.
- **Ground Truth Isolation**: `data/evaluation/ground_truth.json` is completely isolated from all API routers and Zetaris queries.

### 8.3 Connecting to Live Zetaris NDP

To switch from `local_fallback` to live Zetaris execution:

1. Copy `backend/.env.example` to `backend/.env`:
   ```bash
   cp backend/.env.example backend/.env
   ```
2. Configure your Zetaris connection parameters:
   ```env
   ZETARIS_ENABLED=true
   ZETARIS_BASE_URL=https://<your-zetaris-ndp-host>:<port>
   ZETARIS_AUTH_MODE=token
   ZETARIS_TOKEN=<your-bearer-token>
   ZETARIS_DATABASE=default
   ```
3. Restart the FastAPI backend. Test connectivity via `GET /api/health/zetaris` or the **Zetaris Layer** tab in the dashboard.


---

# Multi-Agent Investigation System

Everything below describes what is implemented and was verified on the development machine (macOS, Nightshift.app with the
Meterless engines installed, Zetaris running in Docker). Anything not verified is listed under **Known limitations**.

## 9. Architecture and data flow

```
Request ─► Scout Intent ─► (validate args, refuse/clarify/route)
              │
              ├─► H-MEM retrieve (prior vetted summaries: context only, never evidence)
              ├─► Markovian validate chunk config; World Model init
              ▼
        ┌──────────────────────── iteration (bounded) ────────────────────────┐
        │ Planner ──► retrieval requests                                       │
        │ Zetaris SQL (code, not a model) ──► incidents + supporting evidence  │
        │ Finder  ──► candidate links ──► World Model (new observation/rev)    │
        │ Deterministic verifier (Python) ──► SUPPORTED / WEAK / UNSUPPORTED   │
        │ Skeptic ──► objections / review status ──► World Model               │
        │ Markovian checkpoint (compact carryover, saved to disk)              │
        └── Skeptic or verifier asks for more? ──► next iteration (Planner) ───┘
              ▼
        Reporter (validated state only) ─► deterministic citation check
              ▼
        H-MEM store (only deterministic-verified, Skeptic-reviewed leads) ─► World Model run status
```

Stopping reasons: `evidence_sufficient`, `planner_concluded`, `no_new_evidence`, `no_supportable_links_found`,
`iteration_limit_reached`, `budget_exhausted` (model-call or time budget), `planner_blocked`, `finder_failed`,
`no_records_found`, `interrupted` (e.g. Zetaris went away; resumable). Defaults: 3 iterations, 24 model calls, 900 s.

| Agent | Role | Default model | Output contract |
|---|---|---|---|
| Planner | Plans retrieval; decides retrieve / conclude / blocked. Never claims records were found. | Lightning 30B A3B | `PlannerDecision` |
| Finder | Analyses records retrieved from Zetaris; proposes links with shared attributes, differences, missing evidence. Exact vs semantic match is labelled. | Lightning 30B A3B | `FinderOutput` |
| Skeptic | Attacks the links (not shown the Finder's score); contradictions, timelines, circularity, alternatives, missing-vs-contrary evidence; can request retrieval. | Nemotron 3 Ultra 550B A55B (falls back to Lightning and says so) | `SkepticReview` |
| Reporter | Writes from validated state only; cites IDs; separates facts from hypotheses. | Lightning 30B A3B | `ReportOutput` |

The deterministic verifier (`backend/app/services/evidence_verifier.py`) is not an agent. It checks that every cited incident/evidence ID exists
in the retrieved Zetaris records and matches its source type, that evidence is actually tied to the link's incidents, quotations appear
verbatim, claimed shared attributes appear in records tied to **both** incidents, stations match, timelines are compatible (missing times
are "indeterminate"), and that duplicate/derivative reports (same camera window, same witness observation, newspaper articles about a
police-recorded incident, repeat reports of one forensic item) are not counted as independent corroboration. Forensic `EXCLUSION`, witness
contradiction flags and CCTV-vs-witness vehicle colour conflicts are surfaced, never merged away. The Reporter's citations are re-checked
afterwards, and open Skeptic objections and contradictions are appended to the report even if the Reporter omitted them.

Scores such as `confidence_score` are **uncalibrated model heuristics**; the API and UI label them as such. No determination of guilt is made.

## 10. Meterless Engines: what is actually used

The engines are the real JavaScript modules shipped in `Nightshift.app/Contents/Resources/engine/js/engine/`, executed through Node
(`backend/app/services/meterless_world/runner.cjs` for World Model, `engine_runner.cjs` for the others). No SDK ships with them; the adapters call
their public `window.RT.*` functions.

| Engine | Module | Operations used in the live path | Where |
|---|---|---|---|
| World Model (shared state) | `worldmodel.js` | `init`/`stats`, `upsertEntity`, `appendObservation` (planner decisions, finder findings per revision, skeptic objections + review status, verifier results, reporter synthesis, run status), `snapshot` | `meterless_service.py` |
| H-MEM (persistent memory) | `hmem.js` | `retrieve` at start (context only); `mineAnswer` at end for deterministic-verified, Skeptic-reviewed SUPPORTED links with no open high-severity objection. H-MEM's own secret gate and confidence floor (0.6) apply; scope-isolated | `meterless_engines.py` (`HMemService`) |
| Scout Intent (routing) | `scout-intents.js` | `detectIntent` on every request; result recorded and used as a safety signal. The app maps requests to investigation intents with deterministic rules and validates every argument first | `ScoutIntentService` |
| Markovian (bounded runs) | `markovian.js` | `validateForRun`/`clampConfig` (chunk config from the iteration budget), `extractCarryover` (compact state through its marker rung, 800-token budget), `buildPrompt` (continuation frame, so later Planner calls get goal + carryover, not history), `computeRunEfficiency` | `MarkovianService` |

Design notes and honest limits:
- Markovian's `run()` loop is not used: it drives a single generator, whereas each iteration here spans several agents and SQL calls. The
  Python orchestrator runs the loop and uses Markovian's validated config, carryover cascade, continuation prompt and efficiency formula.
  Run state (`WorkingState`: objective, completed steps, retrieval requests, evidence references, validated findings, objections, outstanding
  tasks, next action, iteration, stopping reason) is saved to `.state/runs/<run_id>.json` and resumed with `continue_from`; evidence is
  rebuilt from Zetaris, not stored.
- Scout Intent's shipped registry (142 entries) targets software-development tasks and has no crime-investigation intents, so its label
  (e.g. `RESEARCH`) is a recorded signal, not the routing decision. Routing intents: `CROSS_STATION_SEARCH`, `COMPARE_INCIDENTS`,
  `INVESTIGATE_RELATIONSHIP`, `REVIEW_CONTRADICTIONS`, `CONTINUE_INVESTIGATION`, `CLARIFY`, `REFUSE`. Routing never executes anything and never bypasses Zetaris or the verifier.
- No official Meterless conformance/evaluation suites are present in the installed app bundle (the engine source files name
  `tests/*-conformance.test.mjs`, which are not shipped). The only engine-provided check run is Scout's built-in `scoutSelfTest` (<16 ms budget).
  Our own tests exercise the real engine modules; they are not Meterless's conformance suites.

## 11. Models verified through Nightshift

Verified on 2026-10-26 against `GET http://127.0.0.1:8088/v1/models` and real calls:

| Role / operation | Requested model | Result |
|---|---|---|
| Planner, Finder, Reporter (and fallback) | `nvidia/nemotron-3.5-lightning-30b-a3b` | Listed; real chat calls succeed (reported model = requested) |
| Skeptic | `nvidia/nemotron-3-ultra-550b-a55b` | Listed; real chat calls succeed (reported model = requested, ~20-40 s per Skeptic call). Needs Nightshift's per-request first-token limit raised: the client sends `meterless-ttfb-ms` (found in Nightshift's proxy source); without it larger prompts returned HTTP 504 and the registry fell back to Lightning |
| Semantic retrieval | `nvidia/nemotron-3-embed-1b` | Listed in `/v1/models`, **but `POST /v1/embeddings` returns HTTP 404 on the running Nightshift process**. Not enabled; not used in retrieval |
| Evidence reranking | Nemotron 3.5 Rerank 8B | **Not listed**, no rerank route found. Not enabled |
| Scout / lightweight planning | Nemotron 3.5 Bolt E4B | **Not listed.** Scout Intent runs as the deterministic JS engine; no LLM is used for routing |

Every model call records requested model, the model the response reports, provider, Nightshift receipt id, latency, token usage, whether a
fallback was used and why. `GET /api/models/registry?probe=true` shows the current verified assignment per role. Reports show per-agent
"answered by" models taken from responses, never from configuration. The API key stays in Nightshift's Providers configuration; the app only holds the local
Nightshift proxy token (read from the Nightshift runtime directory or `NIGHTSHIFT_API_KEY`) and never exposes it to the frontend or logs.

## 12. Zetaris tables and SQL retrieval

Tables (default namespace `lightning.ndp_filestore`, from `.env`): `police_incidents`, `cctv_reports`, `witness_reports`,
`forensic_reports`, `newspaper_reports`. Retrieval is executed by code in `zetaris_investigation_service.py` through the existing
`ZetarisAdapter`: per-station candidate search (`LIKE` on `method_description` / `property_involved`, optional crime type and date range, bounded `LIMIT`),
`get_incidents_by_ids`, `get_incidents_by_locations`, and supporting-evidence queries linked by incident ID or `location_id` (bounded per source).
Models only see a bounded, compacted subset (<= 14 incidents, <= 8 records per source); records are never invented by a model and every ID a model cites is re-checked.
Zetaris outages raise explicit errors (HTTP 502/503) when nothing was retrieved yet, or produce a resumable `interrupted` partial result.
Live mode never falls back to sample or local data.

## 13. Configuration reference (`backend/.env`, see `.env.example`)

| Variable | Default | Meaning |
|---|---|---|
| `ZETARIS_*` | see `.env.example` | Zetaris connection and table names |
| `NIGHTSHIFT_BASE_URL`, `NIGHTSHIFT_API_KEY`, `NIGHTSHIFT_APP_NAME` | `http://127.0.0.1:8088/v1`, auto-read proxy token | Nightshift endpoint/auth |
| `NIGHTSHIFT_MODEL` | `nvidia/nemotron-3.5-lightning-30b-a3b` | Default text model and fallback |
| `NIGHTSHIFT_MODEL_PLANNER` / `_FINDER` / `_REPORTER` | blank = Lightning | Per-role chat model |
| `NIGHTSHIFT_MODEL_SKEPTIC` | `nvidia/nemotron-3-ultra-550b-a55b` | Skeptic model (falls back to Lightning if unlisted/failing) |
| `NIGHTSHIFT_MODEL_EMBEDDING` / `_RERANK` | embed-1b / blank | Probed only; not used in retrieval |
| `NIGHTSHIFT_MODEL_FALLBACK`, `NIGHTSHIFT_SKEPTIC_TIMEOUT_SECONDS` | blank (= `NIGHTSHIFT_MODEL`), 180 | |
| `WORKFLOW_MAX_ITERATIONS` / `_MAX_MODEL_CALLS` / `_TIME_BUDGET_SECONDS` | 3 / 24 / 900 | Hard bounds (model-call budget is checked before each agent call; one agent call may use up to 3 requests for repair/fallback) |
| `WORKFLOW_RETRIEVAL_LIMIT`, `WORKFLOW_EVIDENCE_LIMIT_PER_SOURCE` | 10 / 8 | SQL result bounds |
| `METERLESS_ENGINE_DIR`, `METERLESS_WORLD_MODEL_PATH`, `METERLESS_WORLD_DIR` | Nightshift.app paths | Engine locations |
| `HMEM_ENABLED`, `HMEM_SCOPE`, `STATE_DIR` | true, `crime-intel`, `../.state` | Persistent memory scope and state dir (gitignored) |
| `SAMPLE_MODE` | false | Explicit offline sample mode |

## 14. Run, test, verify

```bash
# Backend (needs Node on PATH and Nightshift.app installed)
cd backend && pip install -r requirements.txt && uvicorn app.main:app --port 8000
# Frontend
cd frontend && npm install && npm run dev

# Tests: unit + mocked + local-engine (live tests skipped)
cd backend && python -m pytest -q
# LIVE integration tests (real Zetaris SQL, Nightshift calls, engines); the full-investigation test takes minutes
cd backend && RUN_LIVE_TESTS=1 python -m pytest -m live -v
# Baseline-vs-multi-agent evaluation (live; writes evaluation/results.json)
python scripts/evaluate_agents.py

# Verify integrations by hand
curl -s localhost:8000/api/models/registry?probe=true | jq .roles
curl -s localhost:8000/api/engines/health | jq .
curl -s localhost:8000/api/ai/diagnostic | jq .
curl -s -XPOST localhost:8000/api/investigations/analyze -H 'content-type: application/json' \
  -d '{"query":"Are INC-NORTH-0042 and INC-CEN-0118 related?"}' | jq '.run_status,.stopping_reason,.agents,.candidate_links'
```

Test taxonomy: `test_model_registry.py`, `test_evidence_verifier.py`, `test_nightshift_client.py` are unit tests with mocks or pure Python;
`test_engine_adapters.py` runs the real engine modules locally (no network); `test_multiagent_workflow.py` uses **mocked model outputs and a mocked Zetaris** with the
**real** World Model/Scout/H-MEM/Markovian engines; `test_investigation_workflow.py` covers the legacy baseline pipeline and the API with mocked Nightshift;
`test_live_integration.py` is the only live suite.

## 15. Sample mode

`SAMPLE_MODE=true` (or `"sample_mode": true` per request) returns one of three labelled, pre-built scenarios - `crowbar_safe_cracking`,
`catalytic_converter`, `keyless_suv_relay` - with `is_sample: true` and `data_mode: sample_mode`. No agent, model, Zetaris query or engine runs, and the UI says so.
Live mode never substitutes sample data; if Zetaris or Nightshift is unconfigured it returns HTTP 503.

## 16. Known limitations

- Embedding retrieval and reranking are **not enabled**: `/v1/embeddings` is 404 on this Nightshift build and no rerank model/route exists. No specialist-retrieval comparison was possible.
- Bolt E4B is not available; Scout Intent's registry has no crime intents (see section 10).
- The Skeptic on Ultra is slow (tens of seconds per call); a full investigation takes roughly 3-6 minutes. The API call is synchronous (no streaming progress); the UI shows the per-iteration trace when the run ends.
- Model outputs are non-deterministic; the evaluation uses one run per case on 7 synthetic cases and is not statistically meaningful.
- The verifier's contradiction/duplicate heuristics cover the data's known patterns (vehicle colour, witness flags, forensic exclusion, repeat CCTV/witness reports); they are not exhaustive.
- H-MEM retrieval is its built-in lexical/hybrid scorer (no vectors, since embeddings are unavailable).
- Zetaris per-source retrieval failures are tolerated and reported in `partial_failures`; SQL is sanitized string interpolation, not bound parameters.
- Meterless engines run only where Nightshift.app is installed.

## 17. AI and Model Usage

All model calls go through Meterless Nightshift to NVIDIA Nemotron models (Lightning 30B A3B; Ultra 550B A55B for the Skeptic). Models plan,
analyse retrieved records, critique, and write the report. They do not access the database directly, and every ID, quotation and attribute they cite is
checked by deterministic code against Zetaris records. Model-generated hypotheses are labelled as hypotheses; scores are uncalibrated.
The data is fully synthetic (fictional stations, people and places). Claude Code (Anthropic) was used to help write this code.

## 18. Third-Party Code and Licences

- Python: FastAPI, Pydantic / pydantic-settings, Starlette, Uvicorn, httpx, python-dotenv, pytest (all permissive open-source licences).
- Frontend: React, Vite, TypeScript, lucide-react (MIT/ISC/Apache-style open-source licences).
- Zetaris NDP (Docker images, used under the licence supplied with them) and Meterless Nightshift + engine modules (proprietary: "Meterless Runtime - Proprietary Software License").
  The engines are **executed from the user's own Nightshift installation**.
- **Action needed before publishing this repository:** `backend/app/services/meterless_world/worldmodel.js` is a byte-for-byte copy of Meterless's proprietary
  `worldmodel.js`, kept as a fallback when Nightshift.app is absent. The Meterless licence grants no right to redistribute it without a written agreement; remove the copy (the adapter uses the installed engine first) or obtain permission.
