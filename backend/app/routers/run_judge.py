"""
Hackathon Judge Entrypoint Router: POST /run
=============================================
Provides the automated evaluation entrypoint required by the Open Agent Hackathon 2026.
Supports single-command execution in live and offline SAMPLE_MODE.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Body, HTTPException, status

from app.config import settings
from app.services.investigation_workflow import investigation_workflow
from app.services.nightshift_client import NightshiftAuthError, NightshiftNotConfiguredError, NightshiftTimeoutError
from app.services.zetaris_adapter import ZetarisConnectionError, ZetarisNotConfiguredError, ZetarisQueryError
from app.services.sample_scenarios import SAMPLE_SCENARIOS, get_sample_investigation
from app.services.trace_logger import TraceLogger

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Judge Path"])


class JudgeRunInput(BaseModel):
    kind: Optional[str] = "scenario"
    scenario_id: Optional[str] = None
    query: Optional[str] = None


class JudgeRunOptions(BaseModel):
    sample_mode: Optional[bool] = None
    force_extract: Optional[bool] = False


class JudgeRunRequest(BaseModel):
    run_id: Optional[str] = None
    scenario_id: Optional[str] = None
    query: Optional[str] = None
    sample_mode: Optional[bool] = None
    input: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None


class LinkAlertItem(BaseModel):
    link_id: str
    source_incident_id: str
    target_incident_id: str
    stations_involved: List[str]
    confidence_score: float
    similarity_basis: str
    supporting_evidence_ids: List[str] = []
    validation_status: Optional[str] = "SUPPORTED"
    contradictions: List[Dict[str, Any]] = []


class JudgeRunResponse(BaseModel):
    run_id: str
    status: str = "success"
    data_mode: str
    scenario_id: str
    summary: str
    alerts: List[LinkAlertItem]
    agents: List[str]
    engines: List[str]
    trace_id: str
    log_file: str
    execution_time_seconds: float


@router.post(
    "/run",
    response_model=JudgeRunResponse,
    summary="Hackathon Judge Replay Entrypoint",
    description="Standardized judge endpoint executing cross-station correlation with full agent tracing.",
)
@router.post("/api/run", response_model=JudgeRunResponse, include_in_schema=False)
async def run_judge_pipeline(req: Optional[JudgeRunRequest] = Body(default=None)) -> JudgeRunResponse:
    start_time = time.perf_counter()
    run_id = (req.run_id if req and req.run_id else None) or f"run-{uuid.uuid4().hex[:12]}"
    
    # Resolve scenario_id and query from various formats
    scenario_id = "crowbar_safe_cracking"
    query = ""
    is_sample = True
    
    if req:
        if req.scenario_id:
            scenario_id = req.scenario_id
        elif req.input and isinstance(req.input, dict) and "scenario_id" in req.input:
            scenario_id = req.input["scenario_id"]
            
        if req.query:
            query = req.query
        elif req.input and isinstance(req.input, dict) and "query" in req.input:
            query = req.input.get("query", "")
            
        if req.sample_mode is not None:
            is_sample = req.sample_mode
        elif req.options and isinstance(req.options, dict) and "sample_mode" in req.options:
            is_sample = req.options["sample_mode"]
        else:
            is_sample = settings.sample_mode or not settings.zetaris_configured

    if scenario_id not in SAMPLE_SCENARIOS:
        scenario_id = "crowbar_safe_cracking"

    # Initialize structured trace logger
    tracer = TraceLogger(run_id=run_id)

    if is_sample:
        return _run_sample(tracer, run_id, scenario_id, query, start_time)
    return await _run_live(tracer, run_id, query, start_time)


def _to_alerts(links: List[Dict[str, Any]]) -> List[LinkAlertItem]:
    return [
        LinkAlertItem(
            link_id=l.get("link_id", f"LNK-{uuid.uuid4().hex[:6]}"),
            source_incident_id=l.get("source_incident_id", ""),
            target_incident_id=l.get("target_incident_id", ""),
            stations_involved=l.get("stations_involved", []),
            confidence_score=float(l.get("confidence_score", 0.0)),
            similarity_basis=l.get("similarity_basis", ""),
            supporting_evidence_ids=l.get("supporting_evidence_ids", []),
            validation_status=l.get("validation_status"),
            contradictions=l.get("contradictions", []),
        )
        for l in links
        if not l.get("withdrawn")
    ]


def _run_sample(tracer: TraceLogger, run_id: str, scenario_id: str, query: str, start_time: float) -> JudgeRunResponse:
    """Replay a pre-built scenario. No agent, model, Zetaris query or engine runs; the trace says so."""
    sample_data = get_sample_investigation(scenario_id, query)
    tracer.log_event(
        step="01_sample_replay",
        agent="SampleMode",
        action="replay_prebuilt_scenario",
        details={"scenario_id": scenario_id, "query": query, "mode": "sample_mode",
                 "note": "Pre-built scenario replayed. No agent, model call, Zetaris query or engine ran."},
        status="ok",
    )
    links = sample_data.get("candidate_links", [])
    tracer.log_event(
        step="02_sample_result",
        agent="SampleMode",
        action="return_candidate_links",
        details={"links": len(links), "link_ids": [l.get("link_id") for l in links]},
        status="ok",
    )
    return JudgeRunResponse(
        run_id=run_id,
        status="success",
        data_mode="sample_mode",
        scenario_id=scenario_id,
        summary=sample_data.get("executive_summary", "Sample scenario replayed."),
        alerts=_to_alerts(links),
        agents=[],
        engines=[],
        trace_id=run_id,
        log_file=str(tracer.log_file.name),
        execution_time_seconds=round(time.perf_counter() - start_time, 4),
    )


async def _run_live(tracer: TraceLogger, run_id: str, query: str, start_time: float) -> JudgeRunResponse:
    """Run the real Planner/Finder/Skeptic/Reporter workflow. Never falls back to sample data."""
    if not settings.zetaris_configured:
        raise HTTPException(status_code=503, detail="Zetaris is NOT CONFIGURED. Set it in .env or use SAMPLE_MODE=true.")
    if not settings.nightshift_configured:
        raise HTTPException(status_code=503, detail="Nightshift is NOT CONFIGURED. Set it in .env or use SAMPLE_MODE=true.")
    if not query:
        raise HTTPException(status_code=422, detail="A live run needs a 'query' (see input_examples/).")

    tracer.log_event(step="01_live_start", agent="Orchestrator", action="run_investigation",
                     details={"query": query, "mode": "zetaris_live"}, status="ok")
    try:
        res = await asyncio.to_thread(investigation_workflow.run_investigation, query=query)
    except (ZetarisNotConfiguredError, NightshiftNotConfiguredError, NightshiftAuthError) as exc:
        tracer.log_event(step="02_live_error", agent="Orchestrator", action="run_investigation", status="error", error=str(exc))
        raise HTTPException(status_code=503, detail=str(exc))
    except (ZetarisConnectionError, ZetarisQueryError) as exc:
        tracer.log_event(step="02_live_error", agent="Orchestrator", action="run_investigation", status="error", error=str(exc))
        raise HTTPException(status_code=502, detail=f"Zetaris query failed: {exc}")
    except NightshiftTimeoutError as exc:
        tracer.log_event(step="02_live_error", agent="Orchestrator", action="run_investigation", status="error", error=str(exc))
        raise HTTPException(status_code=504, detail=f"Nightshift timed out: {exc}")

    for n, call in enumerate(res.get("model_calls") or [], 1):
        tracer.log_event(step=f"model_call_{n:02d}", agent=str(call.get("agent", "model")), action="model_call",
                         provider_meta=call, status="ok")
    for n, op in enumerate(res.get("engine_operations") or [], 1):
        tracer.log_event(step=f"engine_op_{n:02d}", agent="Meterless", action="engine_operation", engine_meta=op, status="ok")
    tracer.log_event(step="99_done", agent="Orchestrator", action="run_complete",
                     details={"run_status": res.get("run_status"), "stopping_reason": res.get("stopping_reason")}, status="ok")

    agents = sorted({a for it in res.get("iterations") or [] for a in it.get("agents", [])})
    engines = sorted({str(op.get("engine")) for op in res.get("engine_operations") or [] if op.get("engine")})
    return JudgeRunResponse(
        run_id=run_id,
        status="success" if res.get("run_status") in (None, "completed") else str(res.get("run_status")),
        data_mode=res.get("data_mode", "zetaris_live"),
        scenario_id=res.get("scenario_id") or "live",
        summary=res.get("executive_summary", ""),
        alerts=_to_alerts(res.get("candidate_links") or []),
        agents=agents,
        engines=engines,
        trace_id=run_id,
        log_file=str(tracer.log_file.name),
        execution_time_seconds=round(time.perf_counter() - start_time, 4),
    )
