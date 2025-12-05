"""Advanced search endpoints for patients."""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date
from database import get_db
from search import PatientSearch
from schemas import Patient
from auth.auth_bearer import get_current_patient
from response import APIResponse
from middleware.rate_limit import limiter
from config import settings
from fastapi import Request

router = APIRouter(prefix="/api/v1/patients", tags=["advanced-search"])


@router.get("/search", response_model=dict, status_code=status.HTTP_200_OK)
async def advanced_search(
    request: Request,
    query: Optional[str] = Query(None, description="General search query (name, email, phone, patient_id)"),
    email: Optional[str] = Query(None, description="Exact email match"),
    phone: Optional[str] = Query(None, description="Phone number search"),
    name: Optional[str] = Query(None, description="Name search (partial match)"),
    gender: Optional[str] = Query(None, description="Gender filter"),
    blood_group: Optional[str] = Query(None, description="Blood group filter"),
    date_of_birth_from: Optional[date] = Query(None, description="Minimum date of birth"),
    date_of_birth_to: Optional[date] = Query(None, description="Maximum date of birth"),
    is_active: Optional[bool] = Query(True, description="Active status filter"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    current_patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    """
    Advanced patient search with multiple filters.
    
    Supports:
    - General search query (searches across name, email, phone, patient_id)
    - Specific field filters (email, phone, name, gender, blood_group)
    - Date range filtering (date_of_birth_from, date_of_birth_to)
    - Active status filtering
    - Sorting and pagination
    """
    if settings.RATE_LIMIT_ENABLED:
        limiter.limit("200/hour")(lambda: None)()
    
    patients, total = await PatientSearch.search(
        db=db,
        query=query,
        email=email,
        phone=phone,
        name=name,
        gender=gender,
        blood_group=blood_group,
        date_of_birth_from=date_of_birth_from,
        date_of_birth_to=date_of_birth_to,
        is_active=is_active,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    correlation_id = getattr(request.state, "correlation_id", None)
    
    return APIResponse.success(
        data=[Patient.model_validate(p).model_dump() for p in patients],
        message="Search completed successfully",
        correlation_id=correlation_id,
        meta={
            "total": total,
            "skip": skip,
            "limit": limit,
            "returned": len(patients),
            "filters": {
                "query": query,
                "email": email,
                "phone": phone,
                "name": name,
                "gender": gender,
                "blood_group": blood_group,
                "date_of_birth_from": str(date_of_birth_from) if date_of_birth_from else None,
                "date_of_birth_to": str(date_of_birth_to) if date_of_birth_to else None,
                "is_active": is_active,
                "sort_by": sort_by,
                "sort_order": sort_order
            }
        }
    ).body

