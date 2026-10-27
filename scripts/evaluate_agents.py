#!/usr/bin/env python3
"""
Evaluate the iterative multi-agent system against the original Lightning-only pipeline.

LIVE: runs both systems against real Zetaris + Nightshift. Ground truth
(data/evaluation/ground_truth.json) is read ONLY here, for scoring; the
application never loads it. Results are measurements on a handful of synthetic
cases with one run each - they are not statistically meaningful.

Usage:  python scripts/evaluate_agents.py [--cases 001,002,...] [--out evaluation/results.json] [--skip-baseline]
"""

from __future__ import annotations

import argparse
import itertools
import os
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")   # Settings reads backend/.env relative to the working directory

from app.config import settings  # noqa: E402
from app.services.evidence_verifier import EvidenceIndex, cluster_independent, detect_contradictions, verify_link  # noqa: E402
from app.services.investigation_workflow import InvestigationWorkflow  # noqa: E402
from app.services.legacy_pipeline_workflow import LegacyInvestigationWorkflow  # noqa: E402
from app.services.nightshift_client import NightshiftClient  # noqa: E402
from app.services.zetaris_investigation_service import ZetarisInvestigationService  # noqa: E402

ID_RE = re.compile(r"\b(?:INC-[A-Z]+-\d+|CCTV-\d+|WIT-\d+|FOR-\d+|EVD-\d+|NEWS-\d+)\b")


def load_truth() -> List[Dict[str, Any]]:
    return json.loads((ROOT / "data/evaluation/ground_truth.json").read_text())


def dataset_ids() -> Set[str]:
    ids: Set[str] = set()
    for name, keys in {"police_incidents": ["incident_id"], "cctv_reports": ["cctv_report_id"], "witness_reports": ["witness_report_id"],
                       "newspaper_reports": ["news_id"], "forensic_reports": ["evidence_report_id", "evidence_item_id"]}.items():
        for r in json.loads((ROOT / f"data/generated/{name}.json").read_text()):
            ids.update(r[k] for k in keys if r.get(k))
    return ids


def build_cases(truth: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id = {t["relationship_id"]: t for t in truth}
    cases = []
    for rid in ("REL-SERIES-001", "REL-SERIES-002", "REL-SERIES-003", "REL-SERIES-004", "REL-SERIES-007"):
        ids = by_id[rid]["incident_ids"]
        cases.append({"case": rid[-3:], "kind": "positive", "incident_ids": ids,
                      "truth_pairs": {frozenset(p) for p in itertools.combinations(ids, 2)},
                      "query": f"Are incidents {', '.join(ids)} related to one another?"})
    for rid, base in (("REL-DISTRACTOR-006", "REL-SERIES-004"), ("REL-DISTRACTOR-008", "REL-SERIES-001")):
        decoy = by_id[rid]["incident_ids"][0]
        base_ids = by_id[base]["incident_ids"][:2]
        ids = [decoy, *base_ids]
        cases.append({"case": rid[-3:], "kind": "decoy", "incident_ids": ids, "decoys": {decoy},
                      "truth_pairs": {frozenset(base_ids)},
                      "query": f"Are incidents {', '.join(ids)} related to one another?"})
    return cases


class CountingClient(NightshiftClient):
    calls = 0

    def generate(self, *a, **k):
        type(self).calls += 1
        return super().generate(*a, **k)


def score(case: Dict[str, Any], res: Dict[str, Any], known_ids: Set[str], active_only: bool = True) -> Dict[str, Any]:
    links = [l for l in res["candidate_links"] if not l.get("withdrawn")] if active_only else res["candidate_links"]
    pairs = {frozenset((l["source_incident_id"], l["target_incident_id"])) for l in links}
    truth = case["truth_pairs"]
    verified = {frozenset((l["source_incident_id"], l["target_incident_id"])) for l in links if l.get("validation_status") in ("SUPPORTED", "WEAK")}
    false_pairs = pairs - truth

    idx = EvidenceIndex()
    idx.add_incidents(res["candidate_incidents"])
    idx.add_evidence(res["supporting_evidence"])
    # Independent re-verification of whatever each system reports.
    reverify = [verify_link({"link_id": l["link_id"], "source_incident_id": l["source_incident_id"], "target_incident_id": l["target_incident_id"],
                             "stations_involved": l["stations_involved"], "supporting_evidence_ids": l["supporting_evidence_ids"],
                             "shared_attributes": l.get("shared_attributes", [])}, idx) for l in links]
    fabricated = [l for l in links if "adjacent county jurisdictions" in (l.get("confidence_rationale") or "")]
    text = " ".join([res["executive_summary"], *res["contradictions_and_limitations"], *res["follow_up_actions"]])
    cited = ID_RE.findall(text) + [i for l in links for i in l["supporting_evidence_ids"]]
    cited_ok = sum(1 for i in cited if i in known_ids)
    rejected = sum(len(l.get("rejected_ids") or []) for l in res["candidate_links"])
    duplicate_links = sum(1 for l in links if cluster_independent([i for i in l["supporting_evidence_ids"] if idx.has(i)], idx,
                                                                  [l["source_incident_id"], l["target_incident_id"]])[1])
    case_ids = [i for i in case["incident_ids"] if idx.has(i)]
    source_contradictions = detect_contradictions(
        case_ids + [i for l in links for i in l["supporting_evidence_ids"]] +
        [r.get("witness_report_id") for r in res["supporting_evidence"].get("witness_reports", []) if r.get("witness_report_id")], idx)
    surfaced = bool([l for l in links if l.get("contradictions")]) or any(
        re.search(r"contradict|conflict|discrepan|inconsisten|dispute|differ", x, re.I) for x in res["contradictions_and_limitations"])
    return {
        "links_reported": len(links), "pairs_reported": sorted(map(sorted, pairs)),
        "valid_link_recall_proposed": round(len(pairs & truth) / len(truth), 3) if truth else None,
        "valid_link_recall_verified": round(len(verified & truth) / len(truth), 3) if truth else None,
        "false_links": len(false_pairs), "decoy_links": sum(1 for p in pairs if p & case.get("decoys", set())),
        "citation_accuracy_final_output": round(cited_ok / len(cited), 3) if cited else None, "cited_ids_final_output": len(cited),
        "raw_model_citations_rejected": rejected,
        "links_not_supported_on_reverification": sum(1 for v in reverify if v.status != "SUPPORTED"),
        "links_unsupported_on_reverification": sum(1 for v in reverify if v.status == "UNSUPPORTED"),
        "fabricated_fallback_links": len(fabricated),
        "links_citing_duplicate_reports": duplicate_links,
        "links_without_any_evidence": sum(1 for l in links if not l["supporting_evidence_ids"]),
        "source_contradictions_present": len(source_contradictions), "contradiction_surfaced_in_output": surfaced,
        "reports_it_reports_duplicates": any(v.duplicate_groups for v in reverify),
    }


def run_one(system: str, case: Dict[str, Any], known: Set[str]) -> Dict[str, Any]:
    t0 = time.time()
    CountingClient.calls = 0
    out: Dict[str, Any] = {"system": system, "case": case["case"], "kind": case["kind"]}
    try:
        if system == "baseline_lightning_only":
            wf = LegacyInvestigationWorkflow(ai_client=CountingClient(settings))
            q0 = wf._data.query_count
            res = wf.run_investigation(query=case["query"], incident_ids=case["incident_ids"])
            out.update(model_calls=CountingClient.calls, sql_queries=wf._data.query_count - q0)
        else:
            wf = InvestigationWorkflow(settings)
            res = wf.run_investigation(query=case["query"], incident_ids=case["incident_ids"])
            out.update(model_calls=res["counts"]["model_calls"], sql_queries=res["counts"]["sql_queries"], iterations=res["iterations_used"],
                       stopping_reason=res["stopping_reason"], run_status=res["run_status"],
                       agent_output_failures=[f for f in res["partial_failures"] if f["component"] in ("planner", "finder", "skeptic", "reporter")],
                       repaired_outputs=sum(1 for c in res["model_calls"] if c.get("status") != "ok"),
                       fallback_to_lightning=any(a["fallback_used"] for a in res["agents"]),
                       models={a["agent"]: a["reported_models"] for a in res["agents"]},
                       skeptic_status=res["skeptic"]["review_status"], open_objections=sum(1 for o in res["skeptic"]["objections"] if o["open"]))
        out["ok"] = True
        out["metrics"] = score(case, res, known)
    except Exception as exc:  # a failed run is data, not something to hide
        out.update(ok=False, error=f"{type(exc).__name__}: {str(exc)[:200]}")
    out["latency_s"] = round(time.time() - t0, 1)
    return out


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    def mean(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else None
    ok = [r for r in rows if r["ok"]]
    m = [r["metrics"] for r in ok]
    pos = [r["metrics"] for r in ok if r["kind"] == "positive"]
    return {
        "runs": len(rows), "failed_runs": len(rows) - len(ok),
        "failure_rate": round((len(rows) - len(ok)) / len(rows), 3) if rows else None,
        "mean_latency_s": mean([r["latency_s"] for r in rows]),
        "mean_model_calls": mean([r.get("model_calls") for r in ok]), "mean_sql_queries": mean([r.get("sql_queries") for r in ok]),
        "valid_link_recall_proposed(positive cases)": mean([x["valid_link_recall_proposed"] for x in pos]),
        "valid_link_recall_verified(positive cases)": mean([x["valid_link_recall_verified"] for x in pos]),
        "false_links_total": sum(x["false_links"] for x in m), "decoy_links_total": sum(x["decoy_links"] for x in m),
        "citation_accuracy_final_output": mean([x["citation_accuracy_final_output"] for x in m]),
        "raw_model_citations_rejected_total": sum(x["raw_model_citations_rejected"] for x in m),
        "links_total": sum(x["links_reported"] for x in m),
        "links_not_supported_on_reverification": sum(x["links_not_supported_on_reverification"] for x in m),
        "links_unsupported_on_reverification": sum(x["links_unsupported_on_reverification"] for x in m),
        "fabricated_fallback_links": sum(x["fabricated_fallback_links"] for x in m),
        "links_citing_duplicate_reports": sum(x["links_citing_duplicate_reports"] for x in m),
        "cases_with_source_contradictions": sum(1 for x in m if x["source_contradictions_present"]),
        "of_which_surfaced_in_output": sum(1 for x in m if x["source_contradictions_present"] and x["contradiction_surfaced_in_output"]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="")
    ap.add_argument("--out", default=str(ROOT / "evaluation/results.json"))
    ap.add_argument("--skip-baseline", action="store_true")
    args = ap.parse_args()
    known = dataset_ids()
    cases = build_cases(load_truth())
    if args.cases:
        want = set(args.cases.split(","))
        cases = [c for c in cases if c["case"] in want]
    systems = ["multi_agent"] if args.skip_baseline else ["baseline_lightning_only", "multi_agent"]
    rows: List[Dict[str, Any]] = []
    for c in cases:
        for s in systems:
            print(f"[{time.strftime('%H:%M:%S')}] {s} case {c['case']} ({c['kind']}) ...", flush=True)
            r = run_one(s, c, known)
            print(f"   -> ok={r['ok']} latency={r['latency_s']}s {r.get('error', '')}", flush=True)
            rows.append(r)
    summary = {s: summarize([r for r in rows if r["system"] == s]) for s in systems}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cases": len(cases),
                                         "summary": summary, "rows": rows}, indent=1, default=str))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
