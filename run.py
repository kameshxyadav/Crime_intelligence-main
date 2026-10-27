#!/usr/bin/env python3
"""
Cross-Station Crime Intelligence — Automated Judge & CLI Runner
==============================================================
Required entrypoint for Open Agent Hackathon 2026.
Supports instant offline execution with --sample-mode or file input.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add backend directory to Python path
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.services.sample_scenarios import SAMPLE_SCENARIOS, get_sample_investigation
from app.services.trace_logger import TraceLogger


def run_cli():
    parser = argparse.ArgumentParser(
        description="Cross-Station Crime Intelligence CLI & Hackathon Judge Runner"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="crowbar_safe_cracking",
        choices=list(SAMPLE_SCENARIOS.keys()),
        help="Predefined cross-station scenario to evaluate",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Path to JSON file containing scenario or incident parameters",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to write execution results JSON",
    )
    parser.add_argument(
        "--sample-mode",
        action="store_true",
        default=True,
        help="Force execution in zero-credential sample mode (default: True)",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="",
        help="Investigative query string",
    )

    args = parser.parse_args()

    start_time = time.perf_counter()
    scenario_id = args.scenario
    query = args.query

    if args.input and os.path.exists(args.input):
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                input_data = json.load(f)
                scenario_id = input_data.get("scenario_id", scenario_id)
                query = input_data.get("query", query)
        except Exception as e:
            print(f"[WARN] Could not parse input file {args.input}: {e}", file=sys.stderr)

    run_id = f"run-cli-{int(time.time())}"
    tracer = TraceLogger(run_id=run_id, base_dir=ROOT_DIR / "logs")

    print("\n" + "=" * 70)
    print(" CROSS-STATION CRIME INTELLIGENCE: AUTOMATED EVALUATION RUN")
    print(" Track 1: Solving Fragmented Intelligence | Open Agent Hackathon 2026")
    print("=" * 70)
    print(f"[*] Run ID       : {run_id}")
    print(f"[*] Scenario     : {scenario_id}")
    print(f"[*] Data Mode    : {'SAMPLE_MODE (offline)' if args.sample_mode else 'LIVE ZETARIS'}")
    print("-" * 70)

    # run.py replays pre-built scenarios (sample mode). For a live multi-agent run use POST /run with
    # Zetaris and Nightshift configured, or POST /api/investigations/analyze.
    tracer.log_event("01_sample_replay", "SampleMode", "replay_prebuilt_scenario",
                     {"scenario": scenario_id, "note": "No agent, model call, Zetaris query or engine ran."})
    print("[*] Replaying a pre-built sample scenario. No agent, model, Zetaris query or engine runs in this CLI.")
    print("[*] For a live run: configure .env and POST /run (see README).")
    sample_data = get_sample_investigation(scenario_id, query)

    elapsed = round(time.perf_counter() - start_time, 4)

    candidate_links = sample_data.get("candidate_links", [])
    print("\n" + "-" * 70)
    print(f" RESULTS FOUND: {len(candidate_links)} Cross-Station Link Alert(s)")
    print("-" * 70)

    for idx, link in enumerate(candidate_links, 1):
        print(f"\n  [ALERT #{idx}] {link.get('link_id', 'LNK-UNKNOWN')}")
        print(f"  Jurisdictions : {' <---> '.join(link.get('stations_involved', []))}")
        print(f"  Confidence    : {link.get('confidence_score', 0.0) * 100:.1f}% ({link.get('validation_status', 'SUPPORTED')})")
        print(f"  Basis         : {link.get('similarity_basis', '')}")
        print(f"  Evidence IDs  : {', '.join(link.get('supporting_evidence_ids', []))}")

    print("\n" + "=" * 70)
    print(f" Execution completed in {elapsed}s | Trace saved: logs/trace-{run_id}.jsonl")
    print("=" * 70 + "\n")

    output_payload = {
        "run_id": run_id,
        "status": "success",
        "scenario_id": scenario_id,
        "data_mode": "sample_mode" if args.sample_mode else "zetaris_live",
        "execution_time_seconds": elapsed,
        "alerts_count": len(candidate_links),
        "alerts": candidate_links,
        "agents": [],
        "engines": [],
        "note": "Sample replay: no agent, model, Zetaris query or engine ran.",
    }

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=2)
        print(f"[+] Output written to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(run_cli())
