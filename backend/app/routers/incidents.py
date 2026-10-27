from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas import DashboardSummary, IncidentListResponse, PoliceIncident
from app.services import dashboard_service

router = APIRouter(prefix="/api", tags=["Dashboard"])

ALLOWED_SORT_FIELDS = {
    "reported_at", "occurred_from", "crime_type",
    "station_id", "status", "estimated_loss",
}


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary():
    result = dashboard_service.get_dashboard_summary()
    return DashboardSummary(**result)


@router.get("/incidents", response_model=IncidentListResponse)
async def list_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, max_length=200),
    station: Optional[str] = Query(None),
    crime_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort_by: str = Query("reported_at"),
    sort_desc: bool = Query(True),
):
    if sort_by not in ALLOWED_SORT_FIELDS:
        sort_by = "reported_at"
    result = dashboard_service.get_incidents(
        page=page,
        page_size=page_size,
        search=search,
        station=station,
        crime_type=crime_type,
        status=status,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )
    return IncidentListResponse(**result)


@router.get("/incidents/{incident_id}", response_model=PoliceIncident)
async def get_incident(incident_id: str):
    record = dashboard_service.get_incident_by_id(incident_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id!r} not found.")
    return PoliceIncident(**record)
