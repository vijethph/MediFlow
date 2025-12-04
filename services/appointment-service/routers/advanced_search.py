"""Advanced search endpoints for appointments."""
from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from database import get_db
from search import AppointmentSearch
from schemas import Appointment
from models import AppointmentStatus, AppointmentPriority
from dependencies import get_current_user
from response import APIResponse
from rate_limit import limiter
from config import Settings
settings = Settings()

router = APIRouter(prefix="/api/v1/appointments", tags=["advanced-search"])


@router.get("/search", response_model=dict, status_code=status.HTTP_200_OK)
async def advanced_search(
    request: Request,
    query: Optional[str] = Query(None, description="General search query"),
    patient_id: Optional[str] = Query(None, description="Patient ID filter"),
    doctor_id: Optional[str] = Query(None, description="Doctor ID filter"),
    doctor_name: Optional[str] = Query(None, description="Doctor name filter"),
    doctor_specialization: Optional[str] = Query(None, description="Doctor specialization filter"),
    status: Optional[AppointmentStatus] = Query(None, description="Status filter"),
    priority: Optional[AppointmentPriority] = Query(None, description="Priority filter"),
    date_from: Optional[datetime] = Query(None, description="Date from filter"),
    date_to: Optional[datetime] = Query(None, description="Date to filter"),
    location: Optional[str] = Query(None, description="Location filter"),
    is_active: Optional[bool] = Query(True, description="Active status filter"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    sort_by: str = Query("appointment_date", description="Field to sort by"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Advanced appointment search with multiple filters."""
    if settings.RATE_LIMIT_ENABLED:
        limiter.limit("200/hour")(lambda: None)()
    
    appointments, total = await AppointmentSearch.search(
        db=db,
        query=query,
        patient_id=patient_id,
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        doctor_specialization=doctor_specialization,
        status=status,
        priority=priority,
        date_from=date_from,
        date_to=date_to,
        location=location,
        is_active=is_active,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    correlation_id = getattr(request.state, "correlation_id", None)
    
    return APIResponse.success(
        data=[Appointment.model_validate(a).model_dump() for a in appointments],
        message="Search completed successfully",
        correlation_id=correlation_id,
        meta={
            "total": total,
            "skip": skip,
            "limit": limit,
            "returned": len(appointments),
            "filters": {
                "query": query,
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "doctor_name": doctor_name,
                "doctor_specialization": doctor_specialization,
                "status": status.value if status else None,
                "priority": priority.value if priority else None,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "location": location,
                "is_active": is_active,
                "sort_by": sort_by,
                "sort_order": sort_order
            }
        }
    ).body

