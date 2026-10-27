# Pre-existing Components Declaration

Everything in this repository was written during the hackathon window (both git commits are dated 2026-10-27), except the components below.

| Component | Pre-existing? | Notes |
|---|---|---|
| FastAPI backend, routers, schemas, agent orchestration (Planner / Finder / Skeptic / Reporter), deterministic evidence verifier, Zetaris adapter, Nightshift client, model registry, trace logger | New | Written for this submission |
| React + TypeScript + Vite frontend (login, overview, investigation workbench, correlation map, incidents, sources, Zetaris status, tip portal) | New | Written for this submission |
| Synthetic dataset generator, 10,000 generated records, 8-scenario ground truth | New | 100% fictional; no real police data or PII |
| Demo video generator (`submission/make_demo_video.py`) | New | Uses Playwright, imageio, Pillow |
| Python libraries: FastAPI, Starlette, Pydantic, pydantic-settings, Uvicorn, httpx, python-dotenv, pytest, pytest-asyncio | Pre-existing, open source | Unmodified, installed via pip |
| JS libraries: React, React DOM, Vite, TypeScript, lucide-react | Pre-existing, open source | Unmodified, installed via npm |
| Zetaris NDP (Docker images) | Pre-existing, sponsor | Used under the licence supplied with it; we wrote only the SQL and adapter code |
| Meterless engines (World Model, H-MEM, Scout Intent, Markovian) from `Nightshift.app` | Pre-existing, sponsor, proprietary | Executed from the user's own Nightshift install via our Node runners (`backend/app/services/meterless_world/*.cjs`). Not redistributed |
| Meterless Nightshift gateway and NVIDIA Nemotron models | Pre-existing, sponsor | Called over the OpenAI-compatible API |
| Claude Code (Anthropic) | Tool | Coding assistant; see `AI_USAGE_AND_RESPONSIBLE_AI.md` |

