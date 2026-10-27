from fastapi import APIRouter
from app import __version__
from app.config import settings
from app.schemas import AppHealthResponse, ZetarisHealthResponse
from app.services import dashboard_service

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("", response_model=AppHealthResponse)
async def app_health():
    return AppHealthResponse(
        status="ok",
        version=__version__,
        environment=settings.app_environment,
    )


@router.get("/zetaris", response_model=ZetarisHealthResponse)
async def zetaris_health():
    result = dashboard_service.get_zetaris_health()
    return ZetarisHealthResponse(**result)
