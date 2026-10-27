"""
Investigations and Agent Intelligence API Router
================================================
Endpoints:
- POST /api/investigations/analyze: Multi-agent cross-station investigation
- GET  /api/investigations/samples: List available offline sample scenarios
- GET  /api/ai/diagnostic: Live diagnostic check for Nightshift + Nemotron
- GET  /api/engine/health: Live health check for Meterless World Model
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query, status

from app.config import settings
from app.schemas import (
    AIDiagnosticResponse,
    EngineHealthResponse,
    InvestigationRequest,
    InvestigationResponse,
)
from app.services.investigation_workflow import investigation_workflow
from app.services.meterless_service import meterless_service
from app.services.nightshift_client import (
    NightshiftAuthError,
    NightshiftClient,
    NightshiftNotConfiguredError,
    NightshiftQueryError,
    NightshiftTimeoutError,
)
from app.services.sample_scenarios import SAMPLE_SCENARIOS, get_sample_investigation
from app.services.zetaris_adapter import (
    ZetarisAuthError,
    ZetarisConnectionError,
    ZetarisNotConfiguredError,
    ZetarisQueryError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Investigations & AI Intelligence"])
ai_client = NightshiftClient(settings)


@router.post(
    "/investigations/analyze",
    response_model=InvestigationResponse,
    summary="Run Cross-Station Investigative Reasoning",
    description=(
        "Executes a multi-agent investigation across North, Central, and Riverside stations. "
        "When live, retrieves records via Zetaris SQL, shares state via Meterless World Model, "
        "and reasons via Nightshift (NVIDIA Nemotron). If sample_mode=true is specified, "
        "returns an isolated, verified sample scenario without claiming live execution."
    ),
)
async def analyze_investigation(req: InvestigationRequest) -> InvestigationResponse:
    # 1. Explicit Sample Mode handling
    use_sample_mode = req.sample_mode if req.sample_mode is not None else settings.sample_mode
    if use_sample_mode:
        logger.info("Executing investigation in SAMPLE MODE (scenario: %s)", req.scenario_id)
        sample_res = get_sample_investigation(req.scenario_id, req.query)
        return InvestigationResponse(**sample_res)

    # 2. Live Mode Pre-flight Checks (Strict: Never silently fall back to sample data)
    if not settings.zetaris_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Zetaris integration is NOT CONFIGURED. Live investigations require active Zetaris NDP. "
                "Set ZETARIS_ENABLED=true in backend/.env or select Sample Mode for demonstration."
            ),
        )

    if not settings.nightshift_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Nightshift AI provider is NOT CONFIGURED. Live investigations require Nightshift on port 8088. "
                "Ensure Nightshift is running and NIGHTSHIFT_BASE_URL is set, or enable Sample Mode."
            ),
        )

    # 3. Execute multi-agent workflow
    try:
        res = investigation_workflow.run_investigation(
            query=req.query,
            incident_ids=req.incident_ids,
            station_ids=req.station_ids,
            crime_type=req.crime_type,
            date_from=req.date_from,
            date_to=req.date_to,
            continue_from=req.continue_from,
        )
        return InvestigationResponse(**res)
    except ZetarisNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Zetaris configuration error: {exc}",
        )
    except (ZetarisConnectionError, ZetarisQueryError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Zetaris SQL query failed: {exc}",
        )
    except (NightshiftNotConfiguredError, NightshiftAuthError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Nightshift AI provider error: {exc}",
        )
    except NightshiftTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Nightshift AI request timed out: {exc}",
        )
    except Exception as exc:
        logger.exception("Unexpected error during investigation analysis: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation analysis failed: {exc}",
        )


@router.get(
    "/investigations/samples",
    summary="List Available Offline Sample Scenarios",
    description="Returns metadata and queries for the 3 documented multi-station sample scenarios.",
)
async def list_sample_scenarios() -> List[Dict[str, Any]]:
    samples = []
    for sc_id, sc in SAMPLE_SCENARIOS.items():
        samples.append({
            "scenario_id": sc_id,
            "title": sc["title"],
            "query": sc["query"],
            "target_stations": sc["target_stations"],
            "crime_type": sc["crime_type"],
            "incidents_count": len(sc["candidate_incidents"]),
            "links_count": len(sc["candidate_links"]),
        })
    return samples


@router.get(
    "/ai/diagnostic",
    response_model=AIDiagnosticResponse,
    summary="Test Nightshift + NVIDIA Nemotron Connectivity",
    description=(
        "Executes a restricted diagnostic request through Nightshift to verify model routing, "
        "reporting model identifier and latency without exposing credentials."
    ),
)
async def ai_diagnostic() -> AIDiagnosticResponse:
    diag = ai_client.diagnostic_check()
    return AIDiagnosticResponse(**diag)


@router.get(
    "/models/registry",
    summary="Nemotron role -> model registry (verified against Nightshift)",
    description="Reports each role's configured model, whether Nightshift lists it, the effective model and fallback. "
                "probe=true makes one real /v1/embeddings call.",
)
async def model_registry_report(probe: bool = Query(False)) -> Dict[str, Any]:
    return investigation_workflow._registry.report(probe=probe)


@router.get(
    "/engines/health",
    summary="Health of all four Meterless Engines",
    description="Runs one real operation per engine (World Model init/stats, Scout detect, H-MEM stats, Markovian config validation).",
)
async def engines_health() -> Dict[str, Any]:
    from app.services.meterless_engines import EngineUnavailableError, HMemService, MarkovianService, ScoutIntentService

    out: Dict[str, Any] = {"world_model": meterless_service.health_check()}
    for name, fn in (("scout_intent", lambda: ScoutIntentService().selftest()),
                     ("h_mem", lambda: HMemService().stats()),
                     ("markovian", lambda: MarkovianService().validate())):
        try:
            _, op = fn()
            out[name] = {**op.as_dict(), "status": "connected"}
        except EngineUnavailableError as exc:
            out[name] = {"status": "error", "message": str(exc)}
    return out


@router.get(
    "/engine/health",
    response_model=EngineHealthResponse,
    summary="Meterless World Model Engine Health",
    description="Probes the local Meterless Engine Node runner and reports schema version and storage status.",
)
async def engine_health() -> EngineHealthResponse:
    h = meterless_service.health_check()
    return EngineHealthResponse(**h)
