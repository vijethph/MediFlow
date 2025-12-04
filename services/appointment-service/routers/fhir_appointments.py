"""FHIR-compliant Appointment API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
try:
    from fhir.resources.appointment import Appointment as FHIRAppointment
    from fhir.resources.bundle import Bundle, BundleEntry
    from fhir.resources.fhirtypes import BundleTypeCode
except ImportError:
    FHIRAppointment = None
    Bundle = None
    BundleEntry = None
    BundleTypeCode = None

from database import get_db
from models import Appointment as DBAppointment
from service import (
    get_appointment,
    get_appointments,
    create_appointment,
    update_appointment
)
from schemas import AppointmentCreate
from fhir.models import FHIRAppointmentConverter, FHIRValidator
from dependencies import get_current_user
from config import Settings
settings = Settings()

router = APIRouter(prefix="/fhir/Appointment", tags=["FHIR"])


@router.get("/{appointment_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def get_fhir_appointment(
    appointment_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get appointment in FHIR R4 format."""
    if not FHIRAppointment:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FHIR resources library not available"
        )
    
    db_appointment = await get_appointment(db, appointment_id)
    
    if not db_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found"
        )
    
    fhir_appointment = FHIRAppointmentConverter.db_to_fhir(db_appointment)
    return fhir_appointment.dict(exclude_none=True)


@router.get("/", response_model=dict, status_code=status.HTTP_200_OK)
async def search_fhir_appointments(
    patient: Optional[str] = Query(None, description="Patient reference"),
    practitioner: Optional[str] = Query(None, description="Practitioner reference"),
    status: Optional[str] = Query(None, description="Appointment status"),
    date: Optional[str] = Query(None, description="Appointment date"),
    _count: int = Query(10, ge=1, le=100),
    _offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search for appointments in FHIR R4 format."""
    if not FHIRAppointment or not Bundle:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FHIR resources library not available"
        )
    
    # Build search query
    appointments = []
    
    if patient:
        patient_id = patient.split("/")[-1] if "/" in patient else patient
        from service import get_appointments_by_patient
        appointments = await get_appointments_by_patient(db, patient_id, skip=_offset, limit=_count)
    elif practitioner:
        practitioner_id = practitioner.split("/")[-1] if "/" in practitioner else practitioner
        from service import get_appointments_by_doctor
        appointments = await get_appointments_by_doctor(db, practitioner_id, skip=_offset, limit=_count)
    else:
        appointments = await get_appointments(db, skip=_offset, limit=_count)
    
    # Convert to FHIR format
    fhir_appointments = [FHIRAppointmentConverter.db_to_fhir(a) for a in appointments]
    
    # Create FHIR Bundle
    bundle_entries = []
    for fhir_appointment in fhir_appointments:
        entry = BundleEntry(
            fullUrl=f"{settings.SERVER_HOST}:{settings.SERVER_PORT}/fhir/Appointment/{fhir_appointment.id}",
            resource=fhir_appointment
        )
        bundle_entries.append(entry)
    
    bundle = Bundle(
        resource_type="Bundle",
        type=BundleTypeCode("searchset"),
        total=len(fhir_appointments),
        entry=bundle_entries
    )
    
    return bundle.dict(exclude_none=True)


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_fhir_appointment(
    fhir_appointment_data: dict,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new appointment from FHIR R4 Appointment resource."""
    if not FHIRAppointment:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FHIR resources library not available"
        )
    
    try:
        fhir_appointment = FHIRAppointment(**fhir_appointment_data)
        
        is_valid, error_message = FHIRValidator.validate_fhir_appointment(fhir_appointment)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid FHIR Appointment resource: {error_message}"
            )
        
        appointment_data = FHIRAppointmentConverter.fhir_to_db(fhir_appointment)
        
        # Create appointment using AppointmentCreate schema
        appointment_create = AppointmentCreate(**appointment_data)
        created_by = current_user.get("email") or current_user.get("user_id")
        db_appointment = await create_appointment(db, appointment_create, created_by=created_by)
        
        created_fhir_appointment = FHIRAppointmentConverter.db_to_fhir(db_appointment)
        return created_fhir_appointment.dict(exclude_none=True)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid FHIR resource format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating appointment: {str(e)}"
        )

