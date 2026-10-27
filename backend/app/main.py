"""
Cross-Station Crime Intelligence — FastAPI backend
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app import __version__
from app.config import settings
from app.routers import auth, health, incidents, investigations, run_judge, sources, tips

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cross-Station Crime Intelligence API",
    description=(
        "Backend API for the Cross-Station Crime Intelligence dashboard. "
        "Serves data from Zetaris NDP (when configured) or local JSON fallback."
    ),
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS — restrict to frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Register routers
app.include_router(run_judge.router)
app.include_router(auth.router)
app.include_router(tips.router)
app.include_router(health.router)
app.include_router(incidents.router)
app.include_router(sources.router)
app.include_router(investigations.router)

# Mount frontend static distribution if built
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if not frontend_dist.exists():
    frontend_dist = Path(__file__).resolve().parent.parent / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


@app.on_event("startup")
async def on_startup():
    logger.info("Cross-Station Crime Intelligence backend starting up")
    logger.info("Environment: %s | Zetaris configured: %s", settings.app_environment, settings.zetaris_configured)
    if not settings.zetaris_configured:
        logger.warning(
            "Zetaris integration is NOT CONFIGURED. "
            "API will serve data from local JSON fallback. "
            "All responses will include data_mode='local_fallback'."
        )
