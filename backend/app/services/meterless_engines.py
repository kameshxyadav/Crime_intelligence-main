"""
Meterless Engine Adapters: Scout Intent, H-MEM, Markovian
=========================================================
Python adapters over the real engine modules installed with Nightshift
(scout-intents.js, hmem.js, markovian.js), executed by
``meterless_world/engine_runner.cjs``. (The fourth engine, World Model, lives
in ``meterless_service.py``.)

Every method returns ``(result, EngineOp)`` so the workflow can put the real
operation, status and latency in the trace. Nothing is simulated: if Node or the
engine file is missing the call raises ``EngineUnavailableError``.

What each engine contributes to the application
  Scout Intent  runs the installed detector on every request; its output is
                recorded and used as a safety signal. The app then maps the
                request onto investigation intents with deterministic rules,
                because the shipped 142-entry registry has no crime-investigation
                intents of its own.
  H-MEM         retrieves prior vetted summaries (context only, never evidence)
                and stores summaries that passed deterministic verification.
  Markovian     validates the run's chunk config, turns the compact working state
                into a budgeted carryover (its marker rung), and builds the
                continuation prompt, so later iterations never resend history.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import Settings, settings

RUNNER = Path(__file__).parent / "meterless_world" / "engine_runner.cjs"
STATIONS = {"NORTH", "CENTRAL", "RIVERSIDE"}
INCIDENT_ID_RE = re.compile(r"^INC-[A-Z]+-\d{3,5}$")
INCIDENT_IN_TEXT_RE = re.compile(r"\bINC-[A-Z]+-\d{3,5}\b")
RUN_ID_RE = re.compile(r"^inv_\d+_[0-9a-f]{6}$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ][\d:.]+Z?)?$")


class EngineUnavailableError(Exception):
    """Engine runner/module could not execute."""


@dataclass
class EngineOp:
    engine: str
    op: str
    status: str                  # ok | error
    latency_ms: float
    detail: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def run_engine(cfg: Settings, engine: str, op: str, args: Dict[str, Any], store_file: Optional[Path] = None,
               timeout: int = 20) -> Tuple[Dict[str, Any], EngineOp]:
    payload = {"engine": engine, "op": op, "args": args, "engineDir": cfg.meterless_engine_dir,
               "storeFile": str(store_file) if store_file else None}
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(["node", str(RUNNER)], input=json.dumps(payload), text=True,
                              capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EngineUnavailableError(f"{engine}.{op}: {exc}") from exc
    ms = (time.perf_counter() - t0) * 1000
    if proc.returncode != 0:
        msg = proc.stderr.strip()[:300]
        try:
            msg = json.loads(proc.stderr).get("error", msg)
        except (ValueError, AttributeError):
            pass
        raise EngineUnavailableError(f"{engine}.{op}: {msg}")
    try:
        out = json.loads(proc.stdout)
    except ValueError as exc:
        raise EngineUnavailableError(f"{engine}.{op}: invalid runner output") from exc
    return out, EngineOp(engine, op, "ok", round(ms, 1))


# ── Scout Intent ─────────────────────────────────────────────────────────────
INTENTS = (
    "CROSS_STATION_SEARCH", "COMPARE_INCIDENTS", "INVESTIGATE_RELATIONSHIP",
    "REVIEW_CONTRADICTIONS", "CONTINUE_INVESTIGATION", "CLARIFY", "REFUSE",
)
_DESTRUCTIVE_DATA_RE = re.compile(
    r"\b(delete|drop|truncate|wipe|erase|destroy)\b.{0,40}\b(table|database|records?|data|logs?|memory|state|evidence)\b", re.I)
_CONTRA_RE = re.compile(r"contradict|conflict|inconsisten|discrepan|disagree", re.I)
_CONTINUE_RE = re.compile(r"\b(continue|resume|pick up)\b", re.I)


@dataclass
class Route:
    intent: str
    query: str
    incident_ids: List[str] = field(default_factory=list)
    station_ids: List[str] = field(default_factory=list)
    crime_type: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    continue_from: Optional[str] = None
    clarification: Optional[str] = None
    refusal: Optional[str] = None
    scout: Dict[str, Any] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ScoutIntentService:
    def __init__(self, cfg: Optional[Settings] = None) -> None:
        self._cfg = cfg or settings

    def detect(self, text: str) -> Tuple[Dict[str, Any], EngineOp]:
        out, op = run_engine(self._cfg, "scout", "detect", {"text": text})
        r = out["result"]
        op.detail = {"mode": r["mode"], "score": r["score"], "tier_hint": r["tierHint"],
                     "engine_ms": r["ms"], "registry_size": r["registrySize"]}
        return r, op

    def selftest(self) -> Tuple[Dict[str, Any], EngineOp]:
        out, op = run_engine(self._cfg, "scout", "selftest", {})
        op.detail = out["result"]
        return out["result"], op

    def route(self, query: str, incident_ids: Optional[List[str]] = None, station_ids: Optional[List[str]] = None,
              crime_type: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None,
              continue_from: Optional[str] = None) -> Tuple[Route, EngineOp]:
        """Classify, validate every argument, and decide the intent. Never executes anything."""
        query = (query or "").strip()
        scout, op = self.detect(query)
        route = Route(intent="CROSS_STATION_SEARCH", query=query, scout={
            "mode": scout["mode"], "score": scout["score"], "tier_hint": scout["tierHint"],
            "candidates": scout.get("candidates", [])[:3]})

        # Validate arguments first: routing may never pass malformed input downstream.
        problems: List[str] = []
        ids = list(dict.fromkeys([*(incident_ids or []), *INCIDENT_IN_TEXT_RE.findall(query)]))
        bad = [i for i in ids if not INCIDENT_ID_RE.match(i)]
        if bad:
            problems.append(f"Invalid incident ID(s): {bad}")
        stations = [s.upper() for s in (station_ids or [])]
        if any(s not in STATIONS for s in stations):
            problems.append(f"Unknown station(s): {[s for s in stations if s not in STATIONS]}; valid: {sorted(STATIONS)}")
        if crime_type and not re.fullmatch(r"[A-Za-z_ ]{2,40}", crime_type):
            problems.append("Invalid crime_type")
        for name, val in (("date_from", date_from), ("date_to", date_to)):
            if val and not ISO_DATE_RE.match(val):
                problems.append(f"{name} must be ISO-8601")
        if continue_from and not RUN_ID_RE.match(continue_from):
            problems.append("continue_from is not a valid investigation ID")
        route.incident_ids = [i for i in ids if INCIDENT_ID_RE.match(i)]
        route.station_ids = [s for s in stations if s in STATIONS]
        route.crime_type, route.date_from, route.date_to = crime_type, date_from, date_to
        route.continue_from = continue_from if continue_from and RUN_ID_RE.match(continue_from) else None

        # Safety: the system is read-only; a request to destroy data is refused, not routed.
        if scout["mode"] == "DESTRUCTIVE" and _DESTRUCTIVE_DATA_RE.search(query):
            route.intent, route.refusal = "REFUSE", "This system is read-only; requests to delete or alter data are not executed."
            route.reasons.append("scout:DESTRUCTIVE + data-mutation phrasing")
            return route, op
        if problems:
            route.intent, route.clarification = "CLARIFY", "; ".join(problems)
            route.reasons.append("argument validation failed")
            return route, op

        mentioned = INCIDENT_IN_TEXT_RE.findall(query)
        if _CONTINUE_RE.search(query) and (route.continue_from or re.search(r"inv_\d+_[0-9a-f]{6}", query)):
            m = re.search(r"inv_\d+_[0-9a-f]{6}", query)
            route.continue_from = route.continue_from or (m.group(0) if m else None)
            route.intent = "CONTINUE_INVESTIGATION"
            route.reasons.append("continue/resume + investigation id")
        elif route.continue_from:
            route.intent = "CONTINUE_INVESTIGATION"
            route.reasons.append("continue_from supplied")
        elif _CONTRA_RE.search(query):
            route.intent = "REVIEW_CONTRADICTIONS"
            route.reasons.append("contradiction vocabulary")
        elif len(route.incident_ids) >= 2 and re.search(r"relat|same|link|connect|series|common", query, re.I):
            route.intent = "INVESTIGATE_RELATIONSHIP"
            route.reasons.append("two incident IDs + relationship vocabulary")
        elif len(route.incident_ids) >= 2:
            route.intent = "COMPARE_INCIDENTS"
            route.reasons.append("two or more incident IDs")
        elif len(query.split()) < 3 and not route.incident_ids:
            route.intent, route.clarification = "CLARIFY", "Please describe what pattern, method, or incidents to investigate."
            route.reasons.append("request too short to act on")
        else:
            route.reasons.append("default: cross-station search")
        return route, op


# ── H-MEM ────────────────────────────────────────────────────────────────────
class HMemService:
    """Persistent memory. Distinct from per-run World Model state."""

    def __init__(self, cfg: Optional[Settings] = None, store_file: Optional[Path] = None) -> None:
        self._cfg = cfg or settings
        self._store = store_file or (self._cfg.state_path / "hmem-knowledge.json")

    def retrieve(self, prompt: str, k: int = 3) -> Tuple[List[Dict[str, Any]], EngineOp]:
        out, op = run_engine(self._cfg, "hmem", "retrieve",
                             {"prompt": prompt, "scope": self._cfg.hmem_scope, "app": "crime-intel", "k": k},
                             store_file=self._store)
        hits = out["result"]["hits"]
        op.detail = {"hits": len(hits), "scope": self._cfg.hmem_scope}
        return hits, op

    def store_verified_summary(self, prompt: str, summary: str, confidence: float, model: str,
                               receipt_id: Optional[str], verified_ids: List[str]) -> Tuple[bool, EngineOp]:
        """
        Only call with text composed from deterministic-verified claims. H-MEM applies
        its own secret gate and confidence floor; we do not bypass either.
        """
        out, op = run_engine(self._cfg, "hmem", "mine", {
            "prompt": prompt, "answer": summary, "scope": self._cfg.hmem_scope, "app": "crime-intel",
            "intent": "investigation", "confidence": confidence, "model": model, "receiptId": receipt_id,
        }, store_file=self._store)
        stored = bool(out["result"]["stored"])
        op.detail = {"stored": stored, "confidence": confidence, "verified_ids": len(verified_ids), "audit": out.get("audit", [])}
        return stored, op

    def stats(self) -> Tuple[Dict[str, Any], EngineOp]:
        out, op = run_engine(self._cfg, "hmem", "stats", {}, store_file=self._store)
        op.detail = out["result"]
        return out["result"], op


# ── Markovian ────────────────────────────────────────────────────────────────
@dataclass
class WorkingState:
    """Compact, resumable investigation state. Evidence is held by reference (IDs), never copied."""
    run_id: str
    objective: str
    intent: str
    iteration: int = 0
    completed_steps: List[str] = field(default_factory=list)
    retrieval_requests: List[Dict[str, Any]] = field(default_factory=list)
    evidence_refs: Dict[str, List[str]] = field(default_factory=dict)
    validated_findings: List[Dict[str, Any]] = field(default_factory=list)
    skeptic_objections: List[Dict[str, Any]] = field(default_factory=list)
    outstanding_tasks: List[str] = field(default_factory=list)
    next_action: str = "plan"
    status: str = "running"            # running | completed | blocked | interrupted | budget_exhausted
    stopping_reason: Optional[str] = None
    model_calls: int = 0
    sql_queries: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MarkovianService:
    def __init__(self, cfg: Optional[Settings] = None) -> None:
        self._cfg = cfg or settings

    def chunk_config(self) -> Dict[str, int]:
        return {"chunkSize": 8000, "maxChunks": max(1, min(32, self._cfg.workflow_max_iterations)),
                "carryoverTokens": 800, "overlapTokens": 0}

    def validate(self) -> Tuple[Dict[str, Any], EngineOp]:
        out, op = run_engine(self._cfg, "markovian", "validate", {"config": self.chunk_config()})
        op.detail = out["result"]["config"]
        return out["result"]["config"], op

    @staticmethod
    def carryover_text(st: WorkingState) -> str:
        """Compact state in the engine's COMPLETED/REMAINING/DECISIONS/CONTEXT shape (references only)."""
        ev = {k: v[:12] for k, v in st.evidence_refs.items()}
        findings = [f"{f['link_id']}:{f['status']}({f['source_incident_id']}~{f['target_incident_id']})" for f in st.validated_findings][:8]
        objs = [f"{o.get('kind')}:{o.get('description', '')[:90]}" for o in st.skeptic_objections if o.get("open", True)][:6]
        return (
            f"COMPLETED: {'; '.join(st.completed_steps[-6:]) or 'none'}\n"
            f"REMAINING: {'; '.join(st.outstanding_tasks[:6]) or 'none'}; next={st.next_action}\n"
            f"DECISIONS: iteration={st.iteration}; findings={json.dumps(findings)}\n"
            f"CONTEXT: evidence_refs={json.dumps(ev)}; open_objections={json.dumps(objs)}"
        )

    def checkpoint(self, st: WorkingState) -> Tuple[str, EngineOp]:
        """Pass the compact state through the engine's carryover cascade (marker rung, budgeted)."""
        chunk = f"iteration {st.iteration} complete\n[STATE_CHECKPOINT]\n{self.carryover_text(st)}"
        out, op = run_engine(self._cfg, "markovian", "extract_carryover",
                             {"chunkText": chunk, "prevCarryover": "", "budgetTokens": self.chunk_config()["carryoverTokens"]})
        r = out["result"]
        op.detail = {"strategy": r["strategy"], "carryover_chars": len(r["carryover"]), "iteration": st.iteration}
        return r["carryover"], op

    def continuation_prompt(self, goal: str, carryover: str) -> Tuple[str, EngineOp]:
        out, op = run_engine(self._cfg, "markovian", "build_prompt",
                             {"mode": "RESEARCH", "isFirst": False, "prompt": goal, "carryover": carryover})
        op.detail = {"prompt_chars": len(out["result"]["prompt"])}
        return out["result"]["prompt"], op

    def efficiency(self, tokens_per_iteration: List[int]) -> Tuple[Dict[str, Any], EngineOp]:
        out, op = run_engine(self._cfg, "markovian", "efficiency",
                             {"chunks": [{"tokens": t} for t in tokens_per_iteration], "config": self.chunk_config()})
        op.detail = out["result"]
        return out["result"], op

    # Resumable state (a crashed or interrupted run is continued, never restarted).
    def _path(self, run_id: str) -> Path:
        if not RUN_ID_RE.match(run_id):
            raise ValueError("invalid run id")
        d = self._cfg.state_path / "runs"
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{run_id}.json"

    def save(self, st: WorkingState, carryover: str) -> None:
        self._path(st.run_id).write_text(json.dumps({"state": st.as_dict(), "carryover": carryover}), encoding="utf-8")

    def load(self, run_id: str) -> Optional[Tuple[WorkingState, str]]:
        p = self._path(run_id)
        if not p.exists():
            return None
        d = json.loads(p.read_text(encoding="utf-8"))
        return WorkingState(**d["state"]), d.get("carryover", "")
