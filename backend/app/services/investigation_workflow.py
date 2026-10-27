"""
Iterative Multi-Agent Investigation Workflow
============================================
Scout Intent -> H-MEM -> Markovian -> [Planner -> Zetaris retrieval -> Finder
-> World Model -> deterministic verifier -> Skeptic]* -> Reporter -> H-MEM.

The loop is conditional: the Skeptic (or a failed deterministic check) can send
the Planner back for more retrieval, and the run ends when the Planner
concludes, nothing new can be retrieved, a budget is hit, or the run is blocked.
Every step is traced to logs/trace-<run_id>.jsonl; every model call records the
model that actually answered. Nothing is defaulted silently: degraded steps are
listed in ``partial_failures``.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Set

from app.config import Settings, settings
from app.services import agents as ag
from app.services.evidence_verifier import (
    EvidenceIndex,
    ClaimValidation,
    verify_cited_ids,
    verify_link,
)
from app.services.meterless_engines import (
    EngineOp,
    EngineUnavailableError,
    HMemService,
    MarkovianService,
    Route,
    ScoutIntentService,
    WorkingState,
)
from app.services.meterless_service import MeterlessWorldModelService, meterless_service
from app.services.model_registry import CallRecord, ModelRegistry
from app.services.nightshift_client import NightshiftClient
from app.services.trace_logger import TraceLogger
from app.services.zetaris_adapter import ZetarisConnectionError, ZetarisNotConfiguredError, ZetarisQueryError
from app.services.zetaris_investigation_service import ZetarisInvestigationService, zetaris_investigation_service

logger = logging.getLogger(__name__)

# Kept for callers/tests that imported it from this module.
_extract_json_block = ag.extract_json_block

ALL_STATIONS = ["NORTH", "CENTRAL", "RIVERSIDE"]


class BudgetExceeded(Exception):
    pass


class _Budget:
    def __init__(self, cfg: Settings) -> None:
        self.max_iterations = cfg.workflow_max_iterations
        self.max_calls = cfg.workflow_max_model_calls
        self.deadline = time.time() + cfg.workflow_time_budget_seconds
        self.calls = 0

    def check(self) -> None:
        if self.calls >= self.max_calls:
            raise BudgetExceeded(f"model-call budget of {self.max_calls} reached")
        if time.time() > self.deadline:
            raise BudgetExceeded("time budget reached")


class InvestigationWorkflow:
    def __init__(
        self,
        cfg: Optional[Settings] = None,
        ai_client: Optional[NightshiftClient] = None,
        world_model: Optional[MeterlessWorldModelService] = None,
        data_service: Optional[ZetarisInvestigationService] = None,
        registry: Optional[ModelRegistry] = None,
        scout: Optional[ScoutIntentService] = None,
        hmem: Optional[HMemService] = None,
        markovian: Optional[MarkovianService] = None,
    ) -> None:
        self._cfg = cfg or settings
        self._ai = ai_client or NightshiftClient(self._cfg)
        self._registry = registry or ModelRegistry(self._cfg, self._ai)
        self._world = world_model or meterless_service
        self._data = data_service or zetaris_investigation_service
        self._scout = scout or ScoutIntentService(self._cfg)
        self._hmem = hmem or HMemService(self._cfg)
        self._markov = markovian or MarkovianService(self._cfg)

    # ── public ───────────────────────────────────────────────────────────
    def run_investigation(
        self,
        query: str,
        incident_ids: Optional[List[str]] = None,
        station_ids: Optional[List[str]] = None,
        crime_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        continue_from: Optional[str] = None,
    ) -> Dict[str, Any]:
        t_start = time.time()
        run = _Run(self, query)
        try:
            return run.execute(incident_ids, station_ids, crime_type, date_from, date_to, continue_from, t_start)
        finally:
            run.close()


class _Run:
    """State and behaviour of one investigation run."""

    def __init__(self, wf: InvestigationWorkflow, query: str) -> None:
        self.wf = wf
        self.cfg = wf._cfg
        self.query = query
        self.run_id = f"inv_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        self.tracer = TraceLogger(self.run_id)
        self.budget = _Budget(self.cfg)
        self.calls: List[CallRecord] = []
        self.engine_ops: List[Dict[str, Any]] = []
        self.partial_failures: List[Dict[str, str]] = []
        self.iterations: List[Dict[str, Any]] = []
        self.index = EvidenceIndex()
        self.incidents: Dict[str, Dict[str, Any]] = {}
        self.evidence: Dict[str, List[Dict[str, Any]]] = {
            "cctv_reports": [], "witness_reports": [], "forensic_reports": [], "newspaper_reports": []}
        self.links: Dict[str, Dict[str, Any]] = {}          # active + withdrawn, latest revision
        self.link_history: List[Dict[str, Any]] = []
        self.validations: Dict[str, ClaimValidation] = {}
        self.last_validation: Dict[str, ClaimValidation] = {}   # latest verdict per link, incl. withdrawn
        self.objections: List[Dict[str, Any]] = []
        self.skeptic_statuses: List[str] = []
        self.unresolved: List[str] = []
        self.executed_fingerprints: Set[str] = set()
        self.tokens_per_iter: List[int] = []
        self.state: Optional[WorkingState] = None
        self.sql_start = wf._data.query_count
        self._evidence_fetched: Set[str] = set()

    def close(self) -> None:
        pass

    # ── trace helpers ────────────────────────────────────────────────────
    def _engine(self, op: EngineOp, step: str, agent: str = "system") -> None:
        d = op.as_dict()
        self.engine_ops.append(d)
        self.tracer.log_event(step=step, agent=agent, action=f"{op.engine}.{op.op}", engine_meta=d, status=op.status, error=op.error)

    def _record_calls(self, calls: List[CallRecord], step: str, agent: str, details: Optional[Dict[str, Any]] = None) -> None:
        for c in calls:
            self.calls.append(c)
            self.budget.calls += 1
            self.tracer.log_event(step=step, agent=agent, action="model_call", provider_meta=c.as_dict(),
                                  details=details, status=c.status, error=c.error)

    def _fail(self, component: str, message: str) -> None:
        self.partial_failures.append({"component": component, "message": message[:300]})
        self.tracer.log_event(step="degraded", agent="system", action=component, status="error", error=message[:300])

    def _call_agent(self, fn, *args, step: str, agent: str):
        self.budget.check()
        try:
            res = fn(self.wf._registry, *args)
        except ag.AgentOutputError as exc:
            self._record_calls(exc.calls, step, agent)
            raise
        except Exception:
            raise
        self._record_calls(res.calls, step, agent, {"repaired": res.repaired})
        return res

    # ── main ─────────────────────────────────────────────────────────────
    def execute(self, incident_ids, station_ids, crime_type, date_from, date_to, continue_from, t_start) -> Dict[str, Any]:
        wf, tracer = self.wf, self.tracer
        tracer.log_event("initialization", "system", "start_investigation",
                         details={"query": self.query, "incident_ids": incident_ids, "station_ids": station_ids})

        # 1. Scout Intent: classify, validate arguments, decide route.
        try:
            route, op = wf._scout.route(self.query, incident_ids, station_ids, crime_type, date_from, date_to, continue_from)
            self._engine(op, "routing", "scout")
        except EngineUnavailableError as exc:
            raise RuntimeError(f"Scout Intent engine unavailable: {exc}") from exc
        tracer.log_event("routing", "scout", "route", details={"intent": route.intent, "reasons": route.reasons,
                                                              "clarification": route.clarification})
        if route.intent in ("REFUSE", "CLARIFY"):
            return self._terminal_response(route, t_start, "refused" if route.intent == "REFUSE" else "needs_clarification")

        resumed = None
        if route.intent == "CONTINUE_INVESTIGATION":
            loaded = wf._markov.load(route.continue_from) if route.continue_from else None
            if not loaded:
                route.intent, route.clarification = "CLARIFY", f"No saved investigation state for {route.continue_from}."
                return self._terminal_response(route, t_start, "needs_clarification")
            st, carry = loaded
            if st.status == "completed":
                route.intent, route.clarification = "CLARIFY", f"Investigation {st.run_id} already completed; start a new one."
                return self._terminal_response(route, t_start, "needs_clarification")
            self.run_id = st.run_id
            self.tracer = tracer = TraceLogger(self.run_id)
            self.state, resumed = st, carry
            self.query = st.objective
            tracer.log_event("initialization", "system", "resume_investigation", details={"iteration": st.iteration, "status": st.status})
        else:
            self.state = WorkingState(run_id=self.run_id, objective=self.query, intent=route.intent)

        st = self.state
        stations = route.station_ids or list(ALL_STATIONS)

        # 2. Markovian: validate the chunk config for this bounded run.
        try:
            cfg_out, op = wf._markov.validate()
            self._engine(op, "initialization", "markovian")
        except EngineUnavailableError as exc:
            raise RuntimeError(f"Markovian engine unavailable: {exc}") from exc

        # 3. World Model + H-MEM context (context only, never evidence).
        memory_context: List[Dict[str, Any]] = []
        try:
            if resumed is None:
                wf._world.init_investigation_state(self.run_id, self.query, stations)
            tracer.log_event("initialization", "system", "world_model.init", engine_meta={"world": f"inv_{self.run_id}"})
        except Exception as exc:
            raise RuntimeError(f"World Model engine unavailable: {exc}") from exc
        if self.cfg.hmem_enabled and resumed is None:
            try:
                memory_context, op = wf._hmem.retrieve(self.query)
                self._engine(op, "memory", "h-mem")
            except EngineUnavailableError as exc:
                self._fail("h-mem.retrieve", str(exc))

        # 4. Rebuild evidence for a resumed run from Zetaris (source of truth).
        if resumed is not None:
            for rq in st.retrieval_requests:
                try:
                    self._execute_request(ag.RetrievalRequest.model_validate(rq), tracer_step="resume_retrieval", count=False)
                except (ZetarisConnectionError, ZetarisQueryError, ZetarisNotConfiguredError) as exc:
                    return self._finish(route, t_start, "interrupted", f"resume_retrieval_failed: {exc}", memory_context)
            self._reindex()

        # 5. Iterate.
        stop_reason = "iteration_limit_reached"
        status = "completed"
        carryover = resumed or ""
        first_iteration = st.iteration + 1
        try:
            for i in range(first_iteration, first_iteration + self.budget.max_iterations):
                st.iteration = i
                it: Dict[str, Any] = {"iteration": i, "agents": [], "new_incidents": 0, "new_evidence": 0}
                calls_before = len(self.calls)

                # Planner
                decision = self._plan(i, route, stations, memory_context, carryover, it)
                if decision.action == "blocked":
                    stop_reason, status = "planner_blocked", "blocked"
                    self.unresolved.extend(decision.outstanding_questions or [decision.rationale])
                    self.iterations.append(it)
                    break
                if decision.action == "conclude" and i > first_iteration:
                    stop_reason = "planner_concluded"
                    it["decision"] = "conclude"
                    self.iterations.append(it)
                    break
                self.unresolved = list(dict.fromkeys([*decision.outstanding_questions, *self.unresolved]))[:12]

                # Retrieval (real Zetaris SQL, executed by code - never by a model)
                before_inc, before_ev = len(self.incidents), len(self._evidence_ids())
                requests = self._bounded_requests(decision, route, stations, i)
                executed = 0
                for rq in requests:
                    fp = json.dumps(rq.model_dump(exclude={"reason"}), sort_keys=True)
                    if fp in self.executed_fingerprints:
                        tracer.log_event("retrieval", "analyst", "skip_duplicate_request", details={"kind": rq.kind})
                        continue
                    self.executed_fingerprints.add(fp)
                    st.retrieval_requests.append(rq.model_dump())
                    self._execute_request(rq, tracer_step="retrieval")
                    executed += 1
                self._auto_supporting_evidence()
                self._reindex()
                it["new_incidents"] = len(self.incidents) - before_inc
                it["new_evidence"] = len(self._evidence_ids()) - before_ev
                st.sql_queries = wf._data.query_count - self.sql_start
                st.completed_steps.append(f"i{i}:retrieved {it['new_incidents']} inc/{it['new_evidence']} ev")
                if not self.incidents:
                    stop_reason, status = "no_records_found", "completed"
                    self.iterations.append(it)
                    break
                if i > first_iteration and executed == 0 and it["new_incidents"] == 0 and it["new_evidence"] == 0:
                    stop_reason = "no_new_evidence"
                    it["decision"] = "stop: nothing new to retrieve"
                    self.iterations.append(it)
                    break

                # Finder
                finder_ok = self._find(i, it)
                if not finder_ok and i == first_iteration:
                    stop_reason, status = "finder_failed", "blocked"
                    self.iterations.append(it)
                    break

                # Deterministic verification
                active = self._active_links()
                self.validations = {l["link_id"]: verify_link(l, self.index) for l in active}
                self.last_validation.update(self.validations)
                vlist = [v.as_dict() for v in self.validations.values()]
                try:
                    wf._world.record_validation(self.run_id, i, vlist)
                    tracer.log_event("validation", "verifier", "verify_links", engine_meta={"world_model": "record_validation"},
                                     details={"statuses": {k: v.status for k, v in self.validations.items()},
                                              "independent_sources": {k: v.independent_source_count for k, v in self.validations.items()}})
                except Exception as exc:
                    self._fail("world_model.record_validation", str(exc))
                it["validation"] = {k: v.status for k, v in self.validations.items()}

                # Skeptic
                review = self._skeptic(i, active, it)

                # Checkpoint (Markovian)
                st.validated_findings = [{"link_id": k, "status": v.status, "source_incident_id": self.links[k]["source_incident_id"],
                                          "target_incident_id": self.links[k]["target_incident_id"]} for k, v in self.validations.items()]
                st.skeptic_objections = [{**o, "open": True} for o in self.objections if o.get("open", True)]
                st.evidence_refs = {"incidents": sorted(self.incidents), "evidence": sorted(self._evidence_ids())}
                wants_more = self._wants_more(review)
                st.outstanding_tasks = [o.get("retrieval_hint") or o["description"][:80] for o in self.objections
                                        if o.get("open", True) and o.get("requests_retrieval")][:6]
                st.next_action = "plan_more_retrieval" if wants_more else "report"
                carryover = self._checkpoint(st)
                it["next_action"] = st.next_action
                self.iterations.append(it)
                self.tokens_per_iter.append(sum(c.completion_tokens or 0 for c in self.calls[calls_before:]))

                if not wants_more:
                    stop_reason = "evidence_sufficient"
                    break
                if i >= first_iteration + self.budget.max_iterations - 1:
                    stop_reason = "iteration_limit_reached"
                    break
        except BudgetExceeded as exc:
            stop_reason, status = f"budget_exhausted: {exc}", "budget_exhausted"
            self._fail("budget", str(exc))
        except (ZetarisConnectionError, ZetarisQueryError, ZetarisNotConfiguredError):
            if not self.incidents:
                raise                       # nothing retrieved yet: surface as a clear API error
            stop_reason, status = "interrupted: Zetaris unavailable", "interrupted"
            self._fail("zetaris", "Zetaris became unavailable mid-run")
        except Exception as exc:            # keep partial state resumable
            logger.exception("Investigation %s interrupted", self.run_id)
            if not self.incidents:
                raise
            stop_reason, status = f"interrupted: {type(exc).__name__}", "interrupted"
            self._fail("workflow", f"{type(exc).__name__}: {exc}")

        if status == "completed" and self.incidents and not any(v.status in ("SUPPORTED", "WEAK") for v in self.validations.values()) and stop_reason in (
                "evidence_sufficient", "planner_concluded", "no_new_evidence", "iteration_limit_reached"):
            stop_reason = f"no_supportable_links_found (after: {stop_reason})"
        return self._finish(route, t_start, status, stop_reason, memory_context)

    # ── Planner ──────────────────────────────────────────────────────────
    def _plan(self, i: int, route: Route, stations: List[str], memory: List[Dict[str, Any]], carryover: str,
              it: Dict[str, Any]) -> ag.PlannerDecision:
        st = self.state
        first = i == 1 or not carryover
        if first:
            mem = [{"memory_id": m["id"], "content": m["content"][:400], "stored_confidence": m["confidence"],
                    "note": "prior vetted summary; NOT evidence for this run"} for m in memory]
            prompt = json.dumps({
                "question": self.query, "intent": route.intent,
                "provided_incident_ids": route.incident_ids, "stations": stations, "crime_type": route.crime_type,
                "date_from": route.date_from, "date_to": route.date_to,
                "database": {"incidents": "police_incidents(incident_id, station_id, crime_type, location_id, occurred_from, "
                                          "occurred_to, method_description, property_involved)",
                             "evidence": "cctv_reports, witness_reports, forensic_reports, newspaper_reports "
                                         "(linked by incident IDs or location_id)"},
                "prior_memory": mem, "iterations_available": self.budget.max_iterations,
                "task": "Plan the first retrieval. Use specific method/property keywords (e.g. tool, vehicle, entry method).",
            }, default=str)
        else:
            frame, op = self.wf._markov.continuation_prompt(self.query, carryover)
            self._engine(op, "planning", "markovian")
            open_obj = [{"kind": o["kind"], "description": o["description"][:200], "hint": o.get("retrieval_hint", ""),
                         "link_id": o.get("link_id")} for o in self.objections if o.get("open", True)][:6]
            prompt = (f"{frame}\n\n[Application note: ignore the marker instructions above; the application records checkpoints. "
                      f"Respond with the JSON object only.]\nOpen Skeptic objections: {json.dumps(open_obj)}\n"
                      f"Iterations remaining after this one: {self.budget.max_iterations - (i - 1) - 1}. "
                      f"Choose action 'retrieve' with new requests if more evidence could resolve an objection, otherwise 'conclude'.")
        try:
            res = self._call_agent(ag.run_planner, prompt, step="planning", agent="planner")
            decision: ag.PlannerDecision = res.parsed  # type: ignore[assignment]
        except (ag.AgentOutputError, BudgetExceeded) as exc:
            if isinstance(exc, BudgetExceeded):
                raise
            self._fail("planner", str(exc))
            decision = ag.PlannerDecision(action="retrieve", rationale="Planner output unusable; deterministic fallback plan.",
                                          retrieval_requests=[])
            it["planner_fallback"] = True
        if decision.action == "conclude" and i == 1:
            decision = decision.model_copy(update={"action": "retrieve", "retrieval_requests": decision.retrieval_requests})
        it["agents"].append("planner")
        it["planner_action"] = decision.action
        try:
            self.wf._world.record_planner_decision(self.run_id, i, {"action": decision.action, "rationale": decision.rationale[:300],
                                                                    "requests": [r.model_dump() for r in decision.retrieval_requests],
                                                                    "outstanding": decision.outstanding_questions})
        except Exception as exc:
            self._fail("world_model.record_planner_decision", str(exc))
        return decision

    def _bounded_requests(self, decision: ag.PlannerDecision, route: Route, stations: List[str], i: int) -> List[ag.RetrievalRequest]:
        reqs = list(decision.retrieval_requests)[:3]
        if i == 1:
            if route.incident_ids and not any(r.kind == "by_incident_ids" for r in reqs):
                reqs.insert(0, ag.RetrievalRequest(kind="by_incident_ids", incident_ids=route.incident_ids, reason="incidents named by the investigator"))
            if not reqs:
                kws = [w for w in re.findall(r"[A-Za-z\-]{4,}", self.query)][:5]
                reqs.append(ag.RetrievalRequest(kind="keyword_search", keywords=kws, station_ids=stations, crime_types=[route.crime_type] if route.crime_type else [],
                                                reason="deterministic fallback keywords from the question"))
        out = []
        for r in reqs[:3]:
            r = r.model_copy(update={
                "station_ids": [s.upper() for s in r.station_ids if s.upper() in ALL_STATIONS] or stations,
                "incident_ids": r.incident_ids[:20], "keywords": r.keywords[:6]})
            if i == 1 and r.kind == "keyword_search":
                r = r.model_copy(update={"date_from": r.date_from or route.date_from, "date_to": r.date_to or route.date_to})
            out.append(r)
        return out

    # ── Retrieval (Zetaris) ─────────────────────────────────────────────
    def _execute_request(self, rq: ag.RetrievalRequest, tracer_step: str, count: bool = True) -> None:
        data, cfg = self.wf._data, self.cfg
        q0, rows_in = data.query_count, 0
        limit = cfg.workflow_retrieval_limit
        found: List[Dict[str, Any]] = []
        if rq.kind == "keyword_search":
            per = max(2, -(-limit // max(1, len(rq.station_ids))))
            for s in rq.station_ids:
                found += data.search_candidate_incidents(keywords=rq.keywords or None, crime_types=rq.crime_types or None,
                                                         station_ids=[s], date_from=rq.date_from, date_to=rq.date_to, limit=per)
            if not found and rq.keywords:
                self.tracer.log_event(tracer_step, "analyst", "broaden_search", details={"reason": "zero rows for keywords", "kind": rq.kind})
                for s in rq.station_ids:
                    found += data.search_candidate_incidents(crime_types=rq.crime_types or None, station_ids=[s],
                                                             date_from=rq.date_from, date_to=rq.date_to, limit=2)
        elif rq.kind == "by_incident_ids":
            found = data.get_incidents_by_ids(rq.incident_ids)
        elif rq.kind == "location_window":
            base = rq.incident_ids or list(self.incidents)
            locs = list({self.incidents[b]["location_id"] for b in base if b in self.incidents and self.incidents[b].get("location_id")})
            found = data.get_incidents_by_locations(locs, limit=limit)
        elif rq.kind == "related_records":
            ids = [x for x in (rq.incident_ids or list(self.incidents)) if x]
            locs = list({self.incidents[b]["location_id"] for b in ids if b in self.incidents and self.incidents[b].get("location_id")})
            self._merge_evidence(data.retrieve_supporting_evidence(ids, locs, self.cfg.workflow_evidence_limit_per_source))
        for r in found:
            if r.get("incident_id"):
                self.incidents.setdefault(r["incident_id"], r)
        self.tracer.log_event(tracer_step, "analyst", f"zetaris_sql:{rq.kind}", status="ok",
                              sql_meta={"queries": data.query_count - q0, "incident_rows": len(found),
                                        "tables": [self.cfg.table_fqn("police_incidents")] if rq.kind != "related_records" else
                                        [self.cfg.table_fqn(t) for t in ("forensic_reports", "cctv_reports", "witness_reports", "newspaper_reports")]},
                              details={"incident_ids": [r.get("incident_id") for r in found][:20], "reason": rq.reason[:160]})

    def _auto_supporting_evidence(self) -> None:
        """Fetch supporting records for incidents whose evidence has not been pulled yet."""
        todo = [i for i in self.incidents if i not in self._evidence_fetched]
        if not todo:
            return
        todo = todo[:20]
        locs = list({self.incidents[i]["location_id"] for i in todo if self.incidents[i].get("location_id")})
        data, q0 = self.wf._data, self.wf._data.query_count
        err0 = len(data.errors)
        self._merge_evidence(data.retrieve_supporting_evidence(todo, locs, self.cfg.workflow_evidence_limit_per_source))
        self._evidence_fetched.update(todo)
        for e in data.errors[err0:]:
            self._fail("zetaris.evidence", e)
        self.tracer.log_event("retrieval", "analyst", "zetaris_sql:supporting_evidence", sql_meta={
            "queries": data.query_count - q0, **{k: len(v) for k, v in self.evidence.items()}},
            details={"incident_ids": todo})

    def _merge_evidence(self, ev: Dict[str, List[Dict[str, Any]]]) -> None:
        keyf = {"cctv_reports": "cctv_report_id", "witness_reports": "witness_report_id",
                "forensic_reports": "evidence_report_id", "newspaper_reports": "news_id"}
        for src, rows in ev.items():
            have = {r.get(keyf[src]) for r in self.evidence[src]}
            for r in rows:
                if r.get(keyf[src]) not in have:
                    self.evidence[src].append(r)

    def _evidence_ids(self) -> Set[str]:
        return self.index.evidence_ids()

    def _reindex(self) -> None:
        self.index = EvidenceIndex()
        self.index.add_incidents(self.incidents.values())
        self.index.add_evidence(self.evidence)

    # ── Finder ───────────────────────────────────────────────────────────
    def _find(self, i: int, it: Dict[str, Any]) -> bool:
        prior = None
        if self.links:
            prior = {
                "previous_links": [{"link_id": k, "withdrawn": l.get("withdrawn", False), "source_incident_id": l["source_incident_id"],
                                    "target_incident_id": l["target_incident_id"],
                                    "verifier_status": self.validations[k].status if k in self.validations else None,
                                    "verifier_explanation": self.validations[k].explanation if k in self.validations else None}
                                   for k, l in self.links.items()],
                "skeptic_objections": [{"link_id": o.get("link_id"), "kind": o["kind"], "description": o["description"][:240]}
                                       for o in self.objections if o.get("open", True)][:8],
                "instruction": "Revise, keep or withdraw links using the new records and objections. Do not ignore objections.",
            }
        try:
            res = self._call_agent(ag.run_finder, list(self.incidents.values()), self.evidence, self.query, prior,
                                   step="analysis", agent="finder")
        except ag.AgentOutputError as exc:
            self._fail("finder", str(exc))
            return False
        it["agents"].append("finder")
        out: ag.FinderOutput = res.parsed  # type: ignore[assignment]
        for lid in out.withdrawn_link_ids:
            if lid in self.links:
                self.links[lid]["withdrawn"] = True
        for l in out.links:
            d = l.model_dump()
            if l.link_id in self.links and self.links[l.link_id].get("withdrawn") is False:
                self.link_history.append({**self.links[l.link_id], "superseded_at_iteration": i})
            d["revision"] = i
            d["withdrawn"] = False
            self.links[l.link_id] = d
            try:
                self.wf._world.record_finder_link(self.run_id, i, d)
            except Exception as exc:
                self._fail("world_model.record_finder_link", str(exc))
        it["links_proposed"] = len(out.links)
        self.tracer.log_event("analysis", "finder", "links_proposed", details={
            "link_ids": [l.link_id for l in out.links], "evidence_ids": sorted({e for l in out.links for e in l.supporting_evidence_ids})[:40]})
        return True

    def _active_links(self) -> List[Dict[str, Any]]:
        return [l for l in self.links.values() if not l.get("withdrawn")]

    # ── Skeptic ──────────────────────────────────────────────────────────
    def _skeptic(self, i: int, active: List[Dict[str, Any]], it: Dict[str, Any]) -> Optional[ag.SkepticReview]:
        if not active:
            self.tracer.log_event("review", "skeptic", "skipped", details={"reason": "no links to review"})
            return None
        summary = [{"link_id": k, "status": v.status, "explanation": v.explanation, "independent_sources": v.independent_source_count,
                    "checks": [{"check": c.check, "status": c.status, "explanation": c.explanation} for c in v.checks if c.status != "pass"],
                    "contradictions": v.contradictions[:4]} for k, v in self.validations.items()]
        try:
            res = self._call_agent(ag.run_skeptic, active, list(self.incidents.values()), self.evidence, summary,
                                   step="review", agent="skeptic")
        except ag.AgentOutputError as exc:
            self._fail("skeptic", str(exc))
            it["skeptic"] = "failed"
            self.skeptic_statuses.append("review_failed")
            return None
        review: ag.SkepticReview = res.parsed  # type: ignore[assignment]
        it["agents"].append("skeptic")
        it["skeptic"] = review.review_status
        self.skeptic_statuses.append(review.review_status)
        # Close earlier objections that this pass no longer raises; keep everything visible.
        for o in self.objections:
            o["open"] = False
        for o in review.objections:
            cited = verify_cited_ids(o.cited_ids, self.index)
            d = o.model_dump()
            d.update({"iteration": i, "open": True, "grounded": not cited["invalid"] or not o.cited_ids,
                      "invalid_cited_ids": cited["invalid"], "valid_cited_ids": cited["valid"]})
            self.objections.append(d)
        try:
            self.wf._world.record_skeptic_review(self.run_id, i, {"review_status": review.review_status,
                                                                   "objections": [o for o in self.objections if o["iteration"] == i]})
        except Exception as exc:
            self._fail("world_model.record_skeptic_review", str(exc))
        self.tracer.log_event("review", "skeptic", "review", details={
            "status": review.review_status, "objections": len(review.objections),
            "ungrounded": sum(1 for o in self.objections if o["iteration"] == i and not o["grounded"])})
        return review

    def _skeptic_completed(self) -> bool:
        return bool(self.skeptic_statuses) and self.skeptic_statuses[-1] in ("accepted", "accepted_with_objections", "needs_more_evidence", "rejected")

    def _wants_more(self, review: Optional[ag.SkepticReview]) -> bool:
        if self.budget.calls >= self.budget.max_calls:
            return False
        skeptic_asks = bool(review) and (review.review_status == "needs_more_evidence"
                                         or any(o.requests_retrieval for o in review.objections))
        unsupported = any(v.status == "UNSUPPORTED" for v in self.validations.values())
        return skeptic_asks or unsupported

    def _checkpoint(self, st: WorkingState) -> str:
        st.model_calls = len(self.calls)
        try:
            carry, op = self.wf._markov.checkpoint(st)
            self._engine(op, "checkpoint", "markovian")
            self.wf._markov.save(st, carry)
            return carry
        except EngineUnavailableError as exc:
            self._fail("markovian.checkpoint", str(exc))
            return self.wf._markov.carryover_text(st)

    # ── Finish ───────────────────────────────────────────────────────────
    def _finish(self, route: Route, t_start: float, status: str, stop_reason: str, memory: List[Dict[str, Any]]) -> Dict[str, Any]:
        wf, st = self.wf, self.state
        assert st is not None
        # Reporter reads validated state only.
        state_view = self._validated_state()
        report: Optional[ag.ReportOutput] = None
        report_model_generated = True
        if self.links or self.incidents:
            try:
                res = self._call_agent(ag.run_reporter, state_view, step="report", agent="reporter")
                report = res.parsed  # type: ignore[assignment]
            except (ag.AgentOutputError, BudgetExceeded) as exc:
                self._fail("reporter", str(exc))
        if report is None:
            report_model_generated = False
            report = self._template_report(state_view, stop_reason)
        report_dict = self._ground_report(report)

        # World Model: reporter synthesis + run status
        try:
            wf._world.record_reporter_synthesis(self.run_id, "final", report.executive_summary[:1200], len(self._active_links()),
                                                len(self._all_contradictions()), report.follow_up_actions)
            wf._world.record_run_status(self.run_id, status, stop_reason, st.iteration)
        except Exception as exc:
            self._fail("world_model.final", str(exc))
        world_state: Dict[str, Any] = {}
        try:
            world_state = wf._world.get_investigation_state(self.run_id)
        except Exception as exc:
            self._fail("world_model.read_state", str(exc))

        # H-MEM: persist only deterministic-verified, source-backed content.
        stored = self._store_memory(route)

        st.status, st.stopping_reason = status, stop_reason
        st.next_action = "none" if status == "completed" else "resume"
        st.sql_queries = wf._data.query_count - self.sql_start
        st.model_calls = len(self.calls)
        st.completed_steps.append(f"report:{status}")
        try:
            wf._markov.save(st, wf._markov.carryover_text(st))
            if len(self.tokens_per_iter) and any(self.tokens_per_iter):
                eff, op = wf._markov.efficiency(self.tokens_per_iter)
                self._engine(op, "completion", "markovian")
        except EngineUnavailableError as exc:
            self._fail("markovian.final", str(exc))

        self.tracer.log_event("completion", "orchestrator", "finalize", details={
            "status": status, "stopping_reason": stop_reason, "iterations": st.iteration, "model_calls": len(self.calls),
            "sql_queries": st.sql_queries, "links_active": len(self._active_links())})
        return self._response(route, report_dict, report_model_generated, world_state, status, stop_reason, t_start, memory, stored)

    # ── validated state / report ─────────────────────────────────────────
    def _all_contradictions(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for v in self.validations.values():
            out += [{**c, "link_id": v.claim_id, "origin": "deterministic_verifier"} for c in v.contradictions]
        out += [{"type": "skeptic_objection", "link_id": o.get("link_id"), "flag": o["kind"], "description": o["description"],
                 "source_ids": o.get("valid_cited_ids", []), "origin": "skeptic", "severity": o["severity"]}
                for o in self.objections if o["kind"] in ("contradiction", "timeline") and o.get("open", True)]
        return out

    def _validated_state(self) -> Dict[str, Any]:
        cited = sorted({e for l in self._active_links() for e in [l["source_incident_id"], l["target_incident_id"], *l["supporting_evidence_ids"]]
                        if self.index.has(e)})
        recs = {i: self._brief(i) for i in cited[:40]}
        return {
            "question": self.query,
            "links": [{**{k: l[k] for k in ("link_id", "source_incident_id", "target_incident_id", "stations_involved", "similarity_basis",
                                           "shared_attributes", "differences", "missing_evidence")},
                       "verifier_status": self.validations[l["link_id"]].status if l["link_id"] in self.validations else None,
                       "independent_sources": self.validations[l["link_id"]].independent_source_count if l["link_id"] in self.validations else 0,
                       "verified_evidence_ids": self.validations[l["link_id"]].verified_evidence_ids if l["link_id"] in self.validations else [],
                       "heuristic_score_uncalibrated": l.get("heuristic_score")} for l in self._active_links()],
            "records": recs,
            "contradictions": self._all_contradictions()[:12],
            "open_skeptic_objections": [{"link_id": o.get("link_id"), "kind": o["kind"], "severity": o["severity"],
                                         "description": o["description"][:260], "cited_ids": o.get("valid_cited_ids", [])}
                                        for o in self.objections if o.get("open", True)],
            "skeptic_review_status": self.skeptic_statuses[-1] if self.skeptic_statuses else "not_run",
            "unresolved_questions": self.unresolved,
            "stopping_reason": self.state.stopping_reason if self.state else None,
            "rule": "Cite only IDs in 'records'. Scores are uncalibrated heuristics, never probabilities.",
        }

    def _brief(self, rid: str) -> Dict[str, Any]:
        e = self.index.get(rid)
        if not e:
            return {}
        r = e["rec"]
        if e["type"] == "police_incident":
            return ag.compact_incident(r)
        comp = ag.compact_evidence({{"cctv": "cctv_reports", "witness": "witness_reports", "forensic": "forensic_reports", "newspaper": "newspaper_reports"}[e["type"]]: [r]}, 1)
        return next((x for v in comp.values() for x in v), {})

    def _template_report(self, state: Dict[str, Any], stop_reason: str) -> ag.ReportOutput:
        n = len(state["links"])
        return ag.ReportOutput(
            title=f"Cross-Station Intelligence Report: {self.query[:60]}",
            executive_summary=(f"[Template report - the Reporter model did not produce valid output.] {n} candidate link(s) were "
                               f"assembled from retrieved records; see verifier status per link. Stopping reason: {stop_reason}. "
                               "Links are investigative leads, not findings of fact."),
            facts=[ag.Fact(statement=f"{l['source_incident_id']} and {l['target_incident_id']} were proposed as related (verifier: {l['verifier_status']}).",
                           source_ids=[l["source_incident_id"], l["target_incident_id"], *l["verified_evidence_ids"][:4]]) for l in state["links"]],
            hypotheses=[ag.Hypothesis(statement=l["similarity_basis"], link_id=l["link_id"]) for l in state["links"]],
        )

    def _ground_report(self, report: ag.ReportOutput) -> Dict[str, Any]:
        """Deterministic post-check of the Reporter: citations must exist; objections cannot be hidden."""
        facts, unverified = [], []
        for f in report.facts:
            chk = verify_cited_ids(f.source_ids, self.index)
            if chk["valid"]:
                facts.append({"statement": f.statement, "source_ids": chk["valid"], "dropped_unknown_ids": chk["invalid"]})
            else:
                unverified.append({"statement": f.statement, "reason": "no cited ID exists in retrieved records",
                                   "cited_ids": f.source_ids})
        limitations = list(report.contradictions_and_limitations)
        low = " ".join(limitations).lower()
        for c in self._all_contradictions():
            if c["description"].lower()[:40] not in low:
                limitations.append(f"[{c['origin']}] {c['description']}")
        for o in self.objections:
            if o.get("open", True) and o["description"].lower()[:40] not in low:
                tag = "missing evidence" if o.get("is_missing_evidence_only") else "objection"
                limitations.append(f"[skeptic {tag}, {o['severity']}] {o['description']}")
        if self._active_links() and not self._skeptic_completed():
            limitations.append("[workflow] No Skeptic review completed for the current links; they have not been independently challenged.")
        for v in self.validations.values():
            if v.status != "SUPPORTED":
                limitations.append(f"[verifier] {v.claim_id} is {v.status}: {v.explanation}")
        return {**report.model_dump(), "facts": facts, "unverified_statements": unverified,
                "contradictions_and_limitations": list(dict.fromkeys(limitations))}

    # ── H-MEM write path ─────────────────────────────────────────────────
    def _store_memory(self, route: Route) -> Dict[str, Any]:
        if not self.cfg.hmem_enabled:
            return {"attempted": False, "reason": "disabled"}
        if self._active_links() and not self._skeptic_completed():
            return {"attempted": False, "reason": "no completed Skeptic review; unchallenged links are never promoted to memory"}
        good = [(k, v) for k, v in self.validations.items() if v.status == "SUPPORTED"]
        high_open = [o for o in self.objections if o.get("open", True) and o["severity"] == "high" and not o.get("is_missing_evidence_only")]
        if not good:
            return {"attempted": False, "reason": "no link passed deterministic verification as SUPPORTED"}
        if high_open:
            return {"attempted": False, "reason": "open high-severity Skeptic objection; nothing promoted to memory"}
        parts = []
        for k, v in good:
            l = self.links[k]
            attrs = "; ".join(f"{a['attribute']}={a['value']}" for a in l["shared_attributes"][:4])
            parts.append(f"Lead (unadjudicated, not a finding of guilt): {l['source_incident_id']} and {l['target_incident_id']} "
                         f"({'/'.join(l['stations_involved'])}) share [{attrs}], corroborated by independent records "
                         f"{', '.join(v.corroborating_ids[:5])}.")
        summary = " ".join(parts) + f" (run {self.run_id}; source IDs verified against Zetaris records at that time.)"
        conf = 0.6 + 0.1 * min(3, min(v.independent_source_count for _, v in good) - 2 + 1) if good else 0.0
        model = next((c.reported_model for c in reversed(self.calls) if c.role == "reporter" and c.reported_model), "none")
        receipt = next((c.receipt_id for c in reversed(self.calls) if c.role == "reporter"), None)
        try:
            ok, op = self.wf._hmem.store_verified_summary(self.query, summary, round(min(conf, 0.9), 2), model, receipt,
                                                          [i for _, v in good for i in v.corroborating_ids])
            self._engine(op, "memory", "h-mem")
            return {"attempted": True, "stored": ok, "retention_weight": round(min(conf, 0.9), 2),
                    "note": "retention weight for H-MEM's floor, not a probability"}
        except EngineUnavailableError as exc:
            self._fail("h-mem.store", str(exc))
            return {"attempted": True, "stored": False, "error": str(exc)[:160]}

    # ── Response ─────────────────────────────────────────────────────────
    def _agents_summary(self) -> List[Dict[str, Any]]:
        out = []
        for role in ("planner", "finder", "skeptic", "reporter"):
            cs = [c for c in self.calls if c.role == role]
            if not cs:
                continue
            out.append({"agent": role, "calls": len(cs),
                        "requested_models": sorted({c.requested_model for c in cs}),
                        "reported_models": sorted({c.reported_model for c in cs if c.reported_model}),
                        "providers": sorted({c.provider for c in cs if c.provider}),
                        "fallback_used": any(c.fallback_used for c in cs),
                        "fallback_reasons": sorted({c.fallback_reason for c in cs if c.fallback_reason}),
                        "errors": [c.error for c in cs if c.error][:3],
                        "avg_latency_ms": round(sum(c.latency_ms or 0 for c in cs) / len(cs), 1)})
        return out

    def _link_models(self) -> List[Dict[str, Any]]:
        res = []
        for k, l in self.links.items():
            v = self.validations.get(k) or self.last_validation.get(k)
            res.append({
                "link_id": k, "source_incident_id": l["source_incident_id"], "target_incident_id": l["target_incident_id"],
                "stations_involved": l.get("stations_involved") or [], "similarity_basis": l.get("similarity_basis", ""),
                "confidence_score": float(l.get("heuristic_score") or 0.0),
                "confidence_rationale": "Uncalibrated Finder heuristic; not a probability. " + (l.get("score_note") or ""),
                "supporting_evidence_ids": (v.verified_evidence_ids if v else []),
                "contradictions": ([*v.contradictions] if v else []),
                "differences_or_inconsistencies": "; ".join(l.get("differences") or []) or None,
                "withdrawn": bool(l.get("withdrawn")),
                "validation_status": v.status if v else None,
                "validation_explanation": v.explanation if v else None,
                "independent_source_count": v.independent_source_count if v else 0,
                "shared_attributes": l.get("shared_attributes", []),
                "missing_evidence": l.get("missing_evidence", []),
                "revision": l.get("revision"),
                "rejected_ids": v.rejected_ids if v else [],
            })
        return res

    def _response(self, route: Route, report: Dict[str, Any], model_generated: bool, world: Dict[str, Any], status: str,
                  stop_reason: str, t_start: float, memory: List[Dict[str, Any]], stored: Dict[str, Any]) -> Dict[str, Any]:
        cfg, st = self.cfg, self.state
        assert st is not None
        stations = sorted({s for l in self.links.values() for s in (l.get("stations_involved") or [])}
                          | {i.get("station_id") for i in self.incidents.values() if i.get("station_id")})
        win = [c for c in self.calls if c.reported_model]
        provider = win[-1].provider if win else None
        links = self._link_models()
        return {
            "investigation_id": self.run_id, "is_sample": False, "data_mode": "zetaris_live", "scenario_id": None,
            "title": report["title"], "query": self.query, "stations_involved": stations,
            "candidate_incidents": list(self.incidents.values()), "supporting_evidence": self.evidence,
            "candidate_links": links,
            "contradictions_and_limitations": report["contradictions_and_limitations"],
            "unresolved_questions": list(dict.fromkeys([*report.get("unresolved_questions", []), *self.unresolved]))[:15],
            "follow_up_actions": report.get("follow_up_actions", []),
            "executive_summary": report["executive_summary"],
            "integration_status": self._integration_status(world, win, provider),
            "retrieval_and_analysis_status": "completed_live" if status == "completed" else status,
            "trace_file": str(self.tracer.log_file.name), "timestamp": time.time(),
            "elapsed_seconds": round(time.time() - t_start, 2),
            # multi-agent additions
            "intent": route.intent, "route": route.as_dict(), "run_status": status, "stopping_reason": stop_reason,
            "iterations": self.iterations, "iterations_used": st.iteration,
            "agents": self._agents_summary(), "model_calls": [c.as_dict() for c in self.calls],
            "engine_operations": self.engine_ops,
            "skeptic": {"review_status": self.skeptic_statuses[-1] if self.skeptic_statuses else "not_run",
                        "history": self.skeptic_statuses, "objections": self.objections},
            "validation_results": [v.as_dict() for v in self.validations.values()],
            "report": {"facts": report["facts"], "hypotheses": report.get("hypotheses", []), "similarities": report.get("similarities", []),
                       "differences": report.get("differences", []), "unverified_statements": report["unverified_statements"],
                       "model_generated": model_generated},
            "memory": {"retrieved": [{"id": m["id"], "content": m["content"][:300], "stored_confidence": m["confidence"],
                                      "note": "prior context, not evidence"} for m in memory], "write": stored},
            "partial_failures": self.partial_failures,
            "counts": {"model_calls": len(self.calls), "sql_queries": st.sql_queries, "iterations": st.iteration},
            "budget": {"max_iterations": self.budget.max_iterations, "max_model_calls": self.budget.max_calls,
                       "time_budget_seconds": cfg.workflow_time_budget_seconds},
            "resume_hint": f"POST /api/investigations/analyze with continue_from={self.run_id}" if status in ("interrupted", "budget_exhausted") else None,
        }

    def _integration_status(self, world: Dict[str, Any], win: List[CallRecord], provider: Optional[str]) -> Dict[str, Any]:
        cfg = self.cfg
        ops: Dict[str, List[Dict[str, Any]]] = {}
        for o in self.engine_ops:
            ops.setdefault(o["engine"], []).append(o)
        def eng(name: str) -> Dict[str, Any]:
            lst = ops.get(name, [])
            return {"status": ("connected" if lst and all(o["status"] == "ok" for o in lst) else ("not_invoked" if not lst else "error")),
                    "operations": sorted({o["op"] for o in lst}), "calls": len(lst)}
        reported = sorted({c.reported_model for c in win if c.reported_model})
        return {
            "zetaris": {"status": "connected", "mode": "zetaris_live", "tables_queried": [
                cfg.table_fqn(t) for t in ("police_incidents", "forensic_reports", "cctv_reports", "witness_reports", "newspaper_reports")]},
            "nightshift_nemotron": {"status": "connected" if win else "no_model_calls", "mode": "nightshift_live",
                                    "model": reported[-1] if reported else cfg.nightshift_model, "models_used": reported,
                                    "provider": provider or "nvidia", "winning_route": None},
            "meterless_engine": {"status": "connected", "mode": "engine_live", "feature": "world_model_shared_state",
                                 "schema_version": 1, "world_name": f"inv_{self.run_id}",
                                 "entities_count": world.get("entities_count", 0), "observations_count": world.get("observations_total", 0),
                                 "contradictions_count": len(world.get("contradictions", []))},
            "meterless_engines": {"world_model": {"status": "connected" if world else "error", "observations_by_kind":
                                                  {k: len(v) for k, v in (world.get("observations_by_kind") or {}).items()}},
                                  "scout_intent": eng("scout"), "h_mem": eng("hmem"), "markovian": eng("markovian")},
            "model_registry": self.wf._registry.report(),
        }

    def _terminal_response(self, route: Route, t_start: float, status: str) -> Dict[str, Any]:
        msg = route.refusal or route.clarification or "No action taken."
        self.tracer.log_event("completion", "scout", status, details={"message": msg})
        return {
            "investigation_id": self.run_id, "is_sample": False, "data_mode": "zetaris_live", "scenario_id": None,
            "title": "Clarification needed" if status == "needs_clarification" else "Request not executed",
            "query": self.query, "stations_involved": [], "candidate_incidents": [],
            "supporting_evidence": {}, "candidate_links": [], "contradictions_and_limitations": [],
            "unresolved_questions": [msg] if status == "needs_clarification" else [], "follow_up_actions": [],
            "executive_summary": msg,
            "integration_status": {"meterless_engines": {"scout_intent": {"status": "connected", "operations": ["detect"], "calls": 1}}},
            "retrieval_and_analysis_status": status, "trace_file": str(self.tracer.log_file.name),
            "timestamp": time.time(), "elapsed_seconds": round(time.time() - t_start, 2),
            "intent": route.intent, "route": route.as_dict(), "run_status": status, "stopping_reason": status,
            "engine_operations": self.engine_ops, "clarification": route.clarification,
            "counts": {"model_calls": 0, "sql_queries": 0, "iterations": 0},
        }


investigation_workflow = InvestigationWorkflow()
