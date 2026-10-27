# Sponsor Technology: Cross-Station Crime Intelligence

> Open Agent Hackathon 2026, Track 1: Solving Fragmented Intelligence

Everything below was checked against the code in this repository. Where something is not enabled or not verified, it says so.

---

## 1. Zetaris NDP: the live data layer

**What it does here.** Zetaris federates five siloed sources, so the agents query them in place instead of loading a merged copy:
`police_incidents`, `cctv_reports`, `witness_reports`, `forensic_reports`, `newspaper_reports` (default namespace `lightning.ndp_filestore`).

**How we use it.**
- `zetaris_adapter.py` talks to Zetaris over its SQL endpoint. Search terms and IDs pass through a character allow-list, and all SQL is read-only `SELECT`.
- `zetaris_investigation_service.py` runs the retrieval *as code*: per-station candidate search (`LIKE` on method and property, optional crime type and date range, bounded `LIMIT`), lookup by incident ID, lookup by `location_id`, and supporting-evidence queries linked by incident ID or location, bounded per source.
- Models never write SQL and never see the database. They get a bounded, compacted subset of the rows Zetaris returned.
- If Zetaris fails mid-run, the run stops as `interrupted` and can be resumed. Live mode never silently substitutes local data.

**Limits.** SQL is sanitised string interpolation, not bound parameters. The `ZetarisAdapter` has a local-JSON fallback for the dashboard pages only, and responses carry a `data_mode` tag.

## 2. Meterless engines and how each is tested

We execute the real JavaScript engine modules shipped in `Nightshift.app` through Node, via `backend/app/services/meterless_world/runner.cjs` and `engine_runner.cjs`. They are not reimplemented in Python. Their tests are in `backend/tests/test_engine_adapters.py` and `test_meterless_engine.py`; they run the real engines locally, with no network.

| Engine | What we use it for | Our tests |
|---|---|---|
| **World Model** (`worldmodel.js`) | Shared state between agents. Entities are upserted; the Planner's decisions, Finder findings (per revision), Skeptic objections and review status, verifier results, the Reporter's synthesis and the run status are all appended as observations. Agents read from this, not from passed-along prose. | `test_real_meterless_engine_world_operations`, `test_meterless_contradiction_preservation`, `test_meterless_agent_provenance`, `test_meterless_health_check` |
| **H-MEM** (`hmem.js`) | Persistent memory. `retrieve` at the start gives prior vetted summaries as context only, never as evidence. `mineAnswer` at the end stores only links that the verifier marked SUPPORTED, the Skeptic reviewed, and that have no open high-severity objection. H-MEM's own secret gate and 0.6 confidence floor apply, and scopes are isolated. | `test_hmem_roundtrip_with_provenance_and_scope_wall`, `test_hmem_refuses_low_confidence_and_secrets` |
| **Scout Intent** (`scout-intents.js`) | `detectIntent` runs on every request and is recorded as a safety signal. Routing itself uses deterministic rules (`CROSS_STATION_SEARCH`, `COMPARE_INCIDENTS`, `INVESTIGATE_RELATIONSHIP`, `REVIEW_CONTRADICTIONS`, `CONTINUE_INVESTIGATION`, `CLARIFY`, `REFUSE`) after arguments are validated. Routing never executes anything. | `test_scout_runs_real_detector`, `test_scout_selftest_runs`, `test_routing_intents`, `test_routing_validates_arguments_before_anything_runs`, `test_routing_refuses_data_mutation_and_never_executes`, `test_destructive_vocabulary_in_a_crime_query_is_not_refused` |
| **Markovian** (`markovian.js`) | Bounded, resumable runs. We use `validateForRun` / `clampConfig` for the iteration budget, `extractCarryover` for a compact state (800-token budget), `buildPrompt` so later Planner calls get goal plus carryover instead of full history, and `computeRunEfficiency`. State is saved to `.state/runs/<run_id>.json`. | `test_markovian_validates_config_and_clamps_iterations`, `test_markovian_rejects_invalid_config`, `test_markovian_carryover_is_compact_and_uses_marker_rung`, `test_markovian_state_resumes_from_disk` |

All four are exercised together by `test_engines_health_endpoint_runs_one_real_operation_per_engine`, and the full agent loop is tested against the real engines with mocked models and a mocked Zetaris in `test_multiagent_workflow.py`.

**Honest limits.**
- Markovian's own `run()` loop is not used. It drives one generator, while each iteration here spans several agents and SQL calls, so our Python orchestrator runs the loop and borrows Markovian's config validation, carryover, continuation prompt and efficiency formula.
- Scout's shipped registry targets software tasks and has no crime intents, so its label is a recorded signal, not the routing decision.
- Our tests exercise the real engine modules but are not Meterless's official conformance suites, which are not shipped in the app bundle. The only engine-provided check we run is Scout's `scoutSelfTest`.
- Engines run only where Nightshift.app is installed. Without it, only sample mode works.

## 3. Meterless Nightshift: the model gateway

- Every model call goes through Nightshift's OpenAI-compatible endpoint (`http://127.0.0.1:8088/v1` by default). The API key stays in Nightshift's Providers configuration; the app holds only the local proxy token and never exposes it to the frontend or logs.
- Each call records the requested model, the model the response reports, provider, Nightshift receipt ID, latency, token usage, and whether a fallback was used and why. Reports show "answered by" from the response, never from configuration.
- For the large Skeptic model the client sends a `meterless-ttfb-ms` header (found in Nightshift's proxy source). Without it, bigger prompts returned HTTP 504 and the registry fell back to Lightning.
- `GET /api/models/registry?probe=true` shows the verified model per role.

## 4. Where NVIDIA contributes

| Role | Model | Verified (2026-10-26, against `/v1/models` and real calls) |
|---|---|---|
| Planner, Finder, Reporter, fallback | `nvidia/nemotron-3.5-lightning-30b-a3b` | Listed; real chat calls succeed |
| Skeptic | `nvidia/nemotron-3-ultra-550b-a55b` | Listed; real calls succeed, about 20 to 40 s each |
| Semantic retrieval | `nvidia/nemotron-3-embed-1b` | Listed, but `POST /v1/embeddings` returns 404. **Not used** |
| Reranking | Nemotron 3.5 Rerank 8B | Not listed. **Not used** |
| Lightweight routing | Nemotron 3.5 Bolt E4B | Not listed. **Not used** |

The small fast model does the high-volume work of planning, finding and writing. The 550B model is spent on the one job where reasoning depth matters most: attacking links to find coincidences, circular evidence, and contradictions. Because the Skeptic never sees the Finder's score, it cannot simply agree with it.

## 5. What is unique

1. **The checker is not a model.** A Python verifier re-checks every ID, quote and shared attribute against the retrieved Zetaris records, and refuses to count duplicate or derivative reports as independent corroboration. Models propose; code disposes.
2. **An independent adversary.** The Skeptic runs on a different, larger model, is blind to the Finder's score, and can request more retrieval.
3. **Contradictions are first-class.** Forensic exclusions, witness conflicts and CCTV-versus-witness colour mismatches reach the final report even if the Reporter omitted them.
4. **Shared state, not shared prose.** Agents coordinate through the World Model's append-only observations, and the run state can be resumed from disk.
5. **No fabricated fallbacks.** Live mode fails loudly with 502 or 503 instead of showing sample data. Sample mode is labelled and claims no agent ran.
6. **Incident-level only.** The system links incidents, never scores people, and leaves every decision to an officer.
