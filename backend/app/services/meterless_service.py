"""
Meterless World Model Service
==============================
Integrates Meterless Engine's World Model (shared state between agents).
Manages shared investigation state across Planner, Analyst, Evaluator,
and Reporter agents:
- Candidate incident links & entities
- Analyst observations & cited evidence IDs
- Evaluator contradictions & revision requests (never overwritten)
- Reporter verified conclusions & follow-up recommendations
- Full agent provenance and timestamps
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import Settings, settings

logger = logging.getLogger(__name__)


class MeterlessEngineError(Exception):
    """Raised when Meterless Engine runner fails."""


class MeterlessWorldModelService:
    """
    Python interface to the Meterless World Model engine.
    Uses the real Meterless Engine runner script backed by worldmodel.js.
    """

    def __init__(self, cfg: Optional[Settings] = None) -> None:
        self._cfg = cfg or settings
        self._runner_path = Path(__file__).parent / "meterless_world" / "runner.cjs"
        self._engine_path = Path(self._cfg.meterless_world_model_path)
        if not self._engine_path.exists():
            # Fallback to local vendored copy in meterless_world/worldmodel.js
            fallback = Path(__file__).parent / "meterless_world" / "worldmodel.js"
            if fallback.exists():
                self._engine_path = fallback

    @property
    def world_dir(self) -> Path:
        if self._cfg.meterless_world_dir:
            p = Path(self._cfg.meterless_world_dir)
        else:
            p = Path.home() / "Library/Application Support/ai.meterless.runtime/world"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def execute_actions(
        self,
        world_name: str,
        actions: List[Dict[str, Any]],
        persist: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute a batch of actions against the Meterless World Model engine.
        Returns parsed engine response.
        """
        input_payload = {
            "worldName": world_name,
            "enginePath": str(self._engine_path) if self._engine_path.exists() else None,
            "worldDir": str(self.world_dir) if persist else None,
            "actions": actions,
        }

        try:
            cmd = ["node", str(self._runner_path)]
            proc = subprocess.run(
                cmd,
                input=json.dumps(input_payload),
                text=True,
                capture_output=True,
                timeout=15,
                check=False,
            )
        except Exception as exc:
            logger.error("Failed to execute Meterless Engine runner: %s", exc)
            raise MeterlessEngineError(f"Meterless Engine execution failed: {exc}") from exc

        if proc.returncode != 0:
            logger.error("Meterless runner exited with code %d: %s", proc.returncode, proc.stderr)
            raise MeterlessEngineError(f"Meterless runner error: {proc.stderr[:300]}")

        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise MeterlessEngineError(f"Invalid JSON from Meterless runner: {proc.stdout[:200]}") from exc

    def init_investigation_state(
        self,
        run_id: str,
        query: str,
        target_stations: List[str],
    ) -> Dict[str, Any]:
        """
        Initialize the shared world state for an investigation run.
        Records the investigation question and target stations.
        """
        world_name = f"inv_{run_id}"
        actions = [
            {"action": "init"},
            {
                "action": "upsert_entity",
                "entity": {
                    "type": "investigation",
                    "name": run_id,
                    "description": f"Investigation: {query}",
                    "traits": ["multi_station_intelligence", *target_stations],
                    "tags": ["INVESTIGATION", *target_stations],
                    "anchors": {"query": query, "stations": target_stations},
                    "provenance": {"agent": "planner", "run_id": run_id, "timestamp": time.time()},
                },
            },
        ]
        res = self.execute_actions(world_name, actions)
        logger.info("Initialized Meterless World Model for investigation run: %s", run_id)
        return res

    def record_candidate_incidents(
        self,
        run_id: str,
        incidents: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Upsert candidate police incident entities into the shared World Model.
        """
        world_name = f"inv_{run_id}"
        actions = []
        for inc in incidents:
            inc_id = inc.get("incident_id", "UNKNOWN")
            station = inc.get("station_id", "UNKNOWN")
            crime_type = inc.get("crime_type", "UNKNOWN")
            loc_id = inc.get("location_id", "")
            method = inc.get("method_description", "")

            actions.append({
                "action": "upsert_entity",
                "entity": {
                    "type": "police_incident",
                    "name": inc_id,
                    "description": method[:200],
                    "traits": [crime_type, station, loc_id],
                    "tags": [crime_type, station],
                    "anchors": {
                        "station_id": station,
                        "location_id": loc_id,
                        "reported_at": inc.get("reported_at"),
                        "status": inc.get("status"),
                        "data_quality": inc.get("data_quality"),
                    },
                    "provenance": {"agent": "analyst", "run_id": run_id, "timestamp": time.time()},
                },
            })

        if not actions:
            return []

        res = self.execute_actions(world_name, actions)
        return res.get("results", [])

    def record_analyst_finding(
        self,
        run_id: str,
        finding_id: str,
        entity_ids: List[str],
        claim: str,
        evidence_ids: List[str],
        stations_involved: List[str],
        similarity_basis: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyst contributes a proposed link or analytical finding to the shared World Model.
        """
        world_name = f"inv_{run_id}"
        obs_id = f"obs_analyst_{finding_id}"
        action = {
            "action": "append_observation",
            "observation": {
                "id": obs_id,
                "kind": "analyst_finding",
                "entityIds": entity_ids,
                "ts": int(time.time() * 1000),
                "payload": {
                    "agent": "analyst",
                    "finding_id": finding_id,
                    "claim": claim,
                    "evidence_ids": evidence_ids,
                    "stations_involved": stations_involved,
                    "similarity_basis": similarity_basis,
                    "metadata": metadata or {},
                    "is_contradiction": False,
                },
            },
        }
        return self.execute_actions(world_name, [action])

    def record_evaluator_feedback(
        self,
        run_id: str,
        feedback_id: str,
        entity_ids: List[str],
        evaluation_verdict: str,  # "CONFIRMED" | "CONTRADICTED" | "INCONCLUSIVE" | "REVISION_REQUESTED"
        claim: str,
        contradiction_flags: List[str],
        unresolved_questions: List[str],
        revision_requested: bool = False,
        missing_evidence_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluator inspects the shared state and records evaluations and contradictions.
        Contradictions are stored explicitly as observations so they are never overwritten.
        """
        world_name = f"inv_{run_id}"
        obs_id = f"obs_eval_{feedback_id}"
        action = {
            "action": "append_observation",
            "observation": {
                "id": obs_id,
                "kind": "evaluator_feedback",
                "entityIds": entity_ids,
                "ts": int(time.time() * 1000),
                "payload": {
                    "agent": "evaluator",
                    "feedback_id": feedback_id,
                    "verdict": evaluation_verdict,
                    "claim": claim,
                    "is_contradiction": len(contradiction_flags) > 0 or evaluation_verdict == "CONTRADICTED",
                    "contradiction_flags": contradiction_flags,
                    "unresolved_questions": unresolved_questions,
                    "revision_requested": revision_requested,
                    "missing_evidence_ids": missing_evidence_ids or [],
                },
            },
        }
        return self.execute_actions(world_name, [action])

    def record_reporter_synthesis(
        self,
        run_id: str,
        synthesis_id: str,
        summary: str,
        candidate_links_count: int,
        contradictions_count: int,
        recommended_actions: List[str],
    ) -> Dict[str, Any]:
        """
        Reporter records final structured synthesis into the shared World Model.
        """
        world_name = f"inv_{run_id}"
        obs_id = f"obs_report_{synthesis_id}"
        action = {
            "action": "append_observation",
            "observation": {
                "id": obs_id,
                "kind": "reporter_synthesis",
                "entityIds": [run_id],
                "ts": int(time.time() * 1000),
                "payload": {
                    "agent": "reporter",
                    "summary": summary,
                    "candidate_links_count": candidate_links_count,
                    "contradictions_count": contradictions_count,
                    "recommended_actions": recommended_actions,
                },
            },
        }
        return self.execute_actions(world_name, [action])


    # ── Multi-agent additions (Finder / Skeptic / Planner / Verifier) ────────
    # World Model observations are immutable and de-duplicated by id, so every
    # revision gets its own id (…_r<n>). Earlier findings, objections and
    # contradictions are therefore preserved rather than overwritten.

    def _append(self, run_id: str, obs_id: str, kind: str, entity_ids: List[str], payload: Dict[str, Any]) -> Dict[str, Any]:
        action = {
            "action": "append_observation",
            "observation": {
                "id": obs_id,
                "kind": kind,
                "entityIds": entity_ids,
                "ts": int(time.time() * 1000),
                "payload": payload,
            },
        }
        return self.execute_actions(f"inv_{run_id}", [action])

    def record_planner_decision(self, run_id: str, iteration: int, decision: Dict[str, Any]) -> Dict[str, Any]:
        return self._append(run_id, f"obs_plan_{run_id}_i{iteration}", "planner_decision", [run_id],
                            {"agent": "planner", "iteration": iteration, **decision})

    def record_finder_link(self, run_id: str, iteration: int, link: Dict[str, Any]) -> Dict[str, Any]:
        link_id = link.get("link_id", "LINK")
        ents = [i for i in (link.get("source_incident_id"), link.get("target_incident_id")) if i]
        return self._append(run_id, f"obs_finder_{link_id}_r{iteration}", "finder_finding", ents or [run_id],
                            {"agent": "finder", "revision": iteration, "link": link})

    def record_skeptic_review(self, run_id: str, iteration: int, review: Dict[str, Any]) -> List[Dict[str, Any]]:
        out = []
        for idx, o in enumerate(review.get("objections", [])):
            out.append(self._append(
                run_id, f"obs_skeptic_{run_id}_i{iteration}_{idx}", "skeptic_objection", [run_id],
                {"agent": "skeptic", "revision": iteration, "is_contradiction": o.get("kind") == "contradiction", **o}))
        out.append(self._append(
            run_id, f"obs_skeptic_status_{run_id}_i{iteration}", "skeptic_review", [run_id],
            {"agent": "skeptic", "revision": iteration, "review_status": review.get("review_status"),
             "objection_count": len(review.get("objections", []))}))
        return out

    def record_validation(self, run_id: str, iteration: int, validations: List[Dict[str, Any]]) -> Dict[str, Any]:
        compact = [{"claim_id": v["claim_id"], "status": v["status"], "independent_source_count": v["independent_source_count"],
                    "source_ids": v["source_ids"], "contradictions": v.get("contradictions", [])} for v in validations]
        return self._append(run_id, f"obs_verify_{run_id}_i{iteration}", "verifier_result", [run_id],
                            {"agent": "verifier", "revision": iteration, "validations": compact,
                             "is_contradiction": any(v.get("contradictions") for v in validations)})

    def record_run_status(self, run_id: str, status: str, stopping_reason: str, iterations: int) -> Dict[str, Any]:
        return self._append(run_id, f"obs_status_{run_id}", "run_status", [run_id],
                            {"agent": "orchestrator", "status": status, "stopping_reason": stopping_reason, "iterations": iterations})

    def get_investigation_state(self, run_id: str) -> Dict[str, Any]:
        """
        Retrieve complete shared state: entities, analyst findings,
        evaluator contradictions, and engine statistics.
        """
        world_name = f"inv_{run_id}"
        actions = [
            {"action": "stats"},
            {"action": "snapshot"},
        ]
        res = self.execute_actions(world_name, actions)
        results = res.get("results", [])

        stats = {}
        entries = []
        for r in results:
            if r.get("action") == "stats":
                stats = r.get("stats", {})
            elif r.get("action") == "snapshot":
                entries = r.get("snapshot", [])

        entities = []
        analyst_findings = []
        evaluator_evaluations = []
        contradictions = []
        reporter_syntheses = []
        by_kind: Dict[str, List[Dict[str, Any]]] = {}

        # Parse snapshot entries: format is [[key, json_string], ...]
        for item in entries:
            if not isinstance(item, list) or len(item) < 2:
                continue
            key, val_str = item[0], item[1]
            try:
                doc = json.loads(val_str) if isinstance(val_str, str) else val_str
            except Exception:
                continue

            if "/entity/" in key:
                entities.append(doc)
            elif "/obs/" in key:
                payload = doc.get("payload") or {}
                kind = doc.get("kind")
                by_kind.setdefault(kind, []).append(doc)
                if kind == "analyst_finding":
                    analyst_findings.append(doc)
                elif kind == "evaluator_feedback":
                    evaluator_evaluations.append(doc)
                    if payload.get("is_contradiction") or payload.get("contradiction_flags"):
                        contradictions.append(doc)
                elif kind == "reporter_synthesis":
                    reporter_syntheses.append(doc)

        contradictions.extend(d for d in by_kind.get("skeptic_objection", []) if (d.get("payload") or {}).get("is_contradiction"))
        contradictions.extend(d for d in by_kind.get("verifier_result", []) if (d.get("payload") or {}).get("is_contradiction"))

        return {
            "world_name": world_name,
            "stats": stats,
            "entities_count": len(entities),
            "observations_count": len(analyst_findings) + len(evaluator_evaluations) + len(reporter_syntheses),
            "entities": entities,
            "analyst_findings": analyst_findings,
            "evaluator_evaluations": evaluator_evaluations,
            "contradictions": contradictions,
            "reporter_syntheses": reporter_syntheses,
            "observations_by_kind": by_kind,
            "observations_total": sum(len(v) for v in by_kind.values()),
            "skeptic_objections": by_kind.get("skeptic_objection", []),
            "finder_findings": by_kind.get("finder_finding", []),
        }

    def health_check(self) -> Dict[str, Any]:
        """Check availability of Meterless World Model engine."""
        try:
            res = self.execute_actions("health_probe", [{"action": "init"}, {"action": "stats"}], persist=False)
            results = res.get("results", [])
            stats = results[1].get("stats", {}) if len(results) > 1 else {}
            return {
                "status": "connected",
                "engine": "meterless_world_model",
                "schema_version": stats.get("schemaVersion", 1),
                "configured": True,
                "engine_path": str(self._engine_path),
                "world_dir": str(self.world_dir),
                "message": "Meterless World Model engine is active and functional.",
            }
        except Exception as exc:
            return {
                "status": "error",
                "engine": "meterless_world_model",
                "schema_version": None,
                "configured": False,
                "engine_path": str(self._engine_path),
                "world_dir": str(self.world_dir),
                "message": f"Meterless World Model engine error: {exc}",
            }


meterless_service = MeterlessWorldModelService()
