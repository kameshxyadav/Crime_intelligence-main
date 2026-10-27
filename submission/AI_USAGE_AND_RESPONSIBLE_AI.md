# AI Usage and Responsible-AI Notes

## AI in the product
- All model calls go through Meterless Nightshift to NVIDIA Nemotron: Lightning 30B A3B (Planner, Finder, Reporter) and Ultra 550B A55B (Skeptic, with a stated fallback to Lightning).
- Models never touch the database. Code runs the SQL; models see a bounded subset (up to 14 incidents, 8 records per source).
- Every ID, quotation and attribute a model cites is re-checked against Zetaris records by deterministic code. Unverifiable citations are rejected.
- Reports show the model that actually answered, taken from the response, not from configuration.

## AI used to build it
- Claude Code (Anthropic) helped write the code, documentation and the demo-video generator.

## Responsible-AI notes
- **No person-level scoring.** Output is about linking incidents. No protected-attribute profiling and no guilt determination.
- **Human in the loop.** Every output is a lead for officer verification, not a finding.
- **Synthetic data only.** Fictional stations, people, plates and companies. No real PII or police records.
- **Uncalibrated scores.** `confidence_score` is a model heuristic, and the API and UI say so.
- **Contradictions are surfaced.** Forensic exclusions, witness contradiction flags and CCTV-versus-witness colour conflicts are shown, not merged away.
- **No silent substitution.** Live mode never falls back to sample or local data. Sample mode is labelled `is_sample: true` and says no agent ran.
- **Ground-truth isolation.** `data/evaluation/ground_truth.json` is never loaded by the app; only the offline evaluation script reads it.
- **Citizen privacy.** The tip portal strips EXIF/GPS in the browser before upload, issues anonymous tracking codes, and screens tips for prompt injection.
- **Bounded runs.** Hard limits on iterations, model calls and time. Every run terminates with a stated reason.

## Limitations
- Embedding retrieval and reranking are not enabled: `/v1/embeddings` returned 404 on the tested Nightshift build, and no rerank route was found.
- The Skeptic on Ultra is slow, so a full live investigation takes about 3 to 6 minutes.
- Model output is non-deterministic. The live evaluation script runs one pass over 7 synthetic cases and is not statistically meaningful.
- Verifier heuristics cover the known patterns in the synthetic data, not all real-world cases.
- The demo login has no password and is for judging only. It is not real authentication.
- `/run`, `run.py` and `SAMPLE_MODE` return pre-built scenarios. They demonstrate the output format, not a live agent run.
- The demo video was recorded in sample mode with no Zetaris or Nightshift running.
