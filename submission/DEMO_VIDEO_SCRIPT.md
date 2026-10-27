# Demo Video Script (target 3:30, limit 4:00)

I can't record video, so this is a shot list and voice-over. Record the screen at 1080p, one take per scene, and trim.

**Before recording**
- Start Zetaris (Docker) and Nightshift. Start the backend and frontend (`README.md`, Host Quick Start).
- A live investigation takes about 3 to 6 minutes. Start it **before** you record and screen-record the finished run, or cut the wait. Say "sped up" on screen if you trim.
- Keep `SAMPLE_MODE=true` as a backup for scene 5, and say it is sample mode if you use it.
- Hide your `.env`, tokens and terminal history.

| Time | Screen | Voice-over |
|---|---|---|
| 0:00 to 0:20 | Title slide, then the Overview page | "A burglar hits a warehouse in one precinct and a jeweller in another. The clues sit in five systems that don't talk to each other. Cross-Station Crime Intelligence connects them, and then tries to disprove its own answer." |
| 0:20 to 0:45 | Sources page and Zetaris status page (green) | "We federate five sources through Zetaris with no ETL: incidents, forensics, CCTV, witnesses and press. 10,000 synthetic records, three fictional precincts, with planted crime rings and decoys." |
| 0:45 to 1:05 | Login page, pick **Crime Analyst** | "Four roles. Citizens and officers are locked out of the analyst tools." Optionally flash the restricted-access screen. |
| 1:05 to 2:20 | Investigation page. Run: *Are INC-NORTH-0042 and INC-CEN-0118 related?* Then the trace | "The Planner, a Nemotron Lightning model, decides what to fetch. Code runs the SQL on Zetaris. The Finder proposes a link: same 36 mm chisel toolmark, same dark grey minivan. Now the part that matters. A Python verifier checks every cited ID and quote against the records. Then the Skeptic, Nemotron Ultra 550B, attacks the link without seeing the Finder's score." |
| 2:20 to 2:50 | Report: link status badges, contradictions section, "answered by" models | "The report cites record IDs. Each link is SUPPORTED, WEAK or UNSUPPORTED. Contradictions stay visible. Scores are labelled uncalibrated, and there is no verdict on guilt." |
| 2:50 to 3:05 | Run the decoy: *Are INC-... (decoy) and the series related?* | "Here's a decoy: a plumbing van reported by a neighbour, excluded by tyre-tread forensics. The system rejects it and shows why." Use the real decoy IDs from `ground_truth.json` (REL-DISTRACTOR-006). |
| 3:05 to 3:20 | Correlation Map page, then Tip Portal (EXIF stripping demo) | "A map of cross-station links, and an anonymous tip portal that strips GPS in the browser and screens for prompt injection." |
| 3:20 to 3:40 | Terminal: `pytest -q` result, `curl /run` | "110 tests pass. The four Meterless engines run for real in tests. One command reproduces the judge path." |
| 3:40 to 3:55 | Closing slide: repo URL | "Models propose, code verifies, a skeptic objects, and the officer decides. Thanks for watching." |

**Don't say** (not true or not verified): "F1 0.926", "100% decoy rejection", "1.24 s per investigation", or "Bolt / embeddings / rerank are used". See `submission/README_NOTES.md`.
