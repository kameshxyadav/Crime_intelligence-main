from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas import IncidentEvidenceResponse, SourceListResponse, SourceRecordsResponse
from app.services import dashboard_service
from app.services.local_data_loader import SOURCE_FILES

router = APIRouter(prefix="/api", tags=["Sources"])

_ALLOWED_SOURCES = set(SOURCE_FILES.keys())


def _validate_source(source_name: str) -> str:
    if source_name not in _ALLOWED_SOURCES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown source {source_name!r}. Allowed: {sorted(_ALLOWED_SOURCES)}",
        )
    return source_name


@router.get("/sources", response_model=SourceListResponse)
async def list_sources():
    sources = dashboard_service.get_sources_info()
    return SourceListResponse(sources=sources, data_mode="local_fallback")


@router.get("/sources/{source_name}/records", response_model=SourceRecordsResponse)
async def list_source_records(
    source_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, max_length=200),
):
    _validate_source(source_name)
    result = dashboard_service.get_source_records(
        source=source_name,
        page=page,
        page_size=page_size,
        search=search,
    )
    return SourceRecordsResponse(**result)


@router.get("/sources/{source_name}/records/{record_id}")
async def get_source_record(source_name: str, record_id: str):
    _validate_source(source_name)
    record = dashboard_service.get_source_record_by_id(source_name, record_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Record {record_id!r} not found in source {source_name!r}.",
        )
    return {"source": source_name, "record": record, "data_mode": "local_fallback"}


@router.get("/incidents/{incident_id}/evidence", response_model=IncidentEvidenceResponse)
async def incident_evidence(incident_id: str):
    result = dashboard_service.get_incident_evidence(incident_id)
    if result.get("incident") is None:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id!r} not found.")
    return IncidentEvidenceResponse(**result)
