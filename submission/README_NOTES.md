# Read before submitting: problems found in the repo

## Fix before making the repo public
1. **Live credentials are committed.** `HANDOFF_CONTEXT.md` contains a Zetaris API token and password (sections 7 and 8). The values and personal file paths have now been scrubbed from the working tree, but they remain in git history (commit `96412ef`). Rotate the token and password, and consider a fresh repo or a history rewrite before publishing.
2. **`docker build` fails on a fresh clone.** The `Dockerfile` does `COPY frontend/dist`, but `frontend/dist/` is gitignored and absent. Run `cd frontend && npm install && npm run build` first, or add a Node build stage to the Dockerfile. I did not run Docker.
3. **Proprietary file warning.** `README.md` section 18 says a copy of Meterless's `worldmodel.js` may be in the repo. I did not find it in the tracked files, but `meterless_service.py` still looks for it as a fallback. Confirm it is not committed.

## Claims in the repo that the code does not support
4. **`output_examples/eval_report.json`** reports F1 0.926 vs 0.304, 100% decoy rejection, and 1.24 s mean runtime. The README says a live investigation takes 3 to 6 minutes, and no `evaluation/results.json` exists. These numbers look hand-written. I left them out of the deck and the form. Either run `python scripts/evaluate_agents.py` and use its output, or delete the file.
5. **`run.py` and `POST /run` are scripted.** They print and log "Skeptic Agent (550B)... PASSED", and `run_judge.py` logs hard-coded "rows_returned: 2" and model names, but no agent, Zetaris query or engine runs. `README.md` says sample mode "runs the REAL Planner/Finder/Skeptic loop"; that is not true of these two paths. Judges who read the trace may call it misleading. Either wire `/run` to the real workflow or relabel its output as a replay.
6. **Old `SPONSOR_TECH.md` and `metadata.json`** described named queries (`q_cross_station_incidents`, etc.) and an H-MEM "human accept/reject, +/-0.08 cap" feature. Neither exists in the code (the query name appears only in a log string). I rewrote `SPONSOR_TECH.md` from the code. `metadata.json` still contains those claims and lists only two engines; update it to match.
7. **"$4,699 DGX Spark Award" qualification** was in the old `SPONSOR_TECH.md`; I removed it because I can't verify the criteria.

## Deliverable status
| # | Item | Status |
|---|---|---|
| 1 | Demo video | `demo_video.mp4` (silent, sample mode) built by `make_demo_video.py`; narration in `DEMO_VIDEO_SCRIPT.md` |
| 2 | Slide deck | `Cross-Station-Crime-Intelligence-Deck.pptx`, 8 slides. **I did not see the 8 required points** (the image only lists "covering the 8 required points"), so I assumed: problem, solution/architecture, sponsor tech, differentiators, results, responsible AI, access. Send me the real list and I'll realign. Layout not visually checked |
| 3 | Public repo + README | README exists; not published. Fix items 1 to 3 first |
| 4 | Sponsor technology | `SPONSOR_TECH.md` (rewritten) |
| 5 | Pre-existing components | `PRE_EXISTING_COMPONENTS.md` |
| 7 | Name, one-liner, descriptions | `PROJECT_DESCRIPTION.md` |
| 8 | AI usage, responsible AI | `AI_USAGE_AND_RESPONSIBLE_AI.md` |
| 10 | Judge logins | `JUDGE_LOGINS.md` |
| 6, 9 | Cursor field, live link | Left out as requested |
