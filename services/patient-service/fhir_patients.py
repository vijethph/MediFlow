"""FHIR-compliant Patient API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
try:
    from fhir.resources.patient import Patient as FHIRPatient
    from fhir.resources.bundle import Bundle, BundleEntry
    from fhir.resources.fhirtypes import BundleTypeCode
except ImportError:
    # Fallback: Create minimal FHIR structures if library not available
    FHIRPatient = None
    Bundle = None
    BundleEntry = None
    BundleTypeCode = None

from database import get_db
from models import Patient as DBPatient
from crud import (
    get_patient,
    get_patient_by_email,
    get_patients,
    create_patient,
    update_patient
)
from schemas import PatientCreate
from fhir.models import FHIRPatientConverter, FHIRValidator
from fhir.schemas import FHIRPatientResponse, FHIRBundle
from auth.auth_bearer import get_current_patient
from config import settings

router = APIRouter(prefix="/fhir/Patient", tags=["FHIR"])


@router.get("/{patient_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def get_fhir_patient(
    patient_id: str,
    current_patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    """
    Get patient in FHIR R4 format.
    
    Returns a FHIR Patient resource for the specified patient ID.
    """
    # Get patient from database
    db_patient = await get_patient(db, patient_id)
    
    if not db_patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found"
        )
    
    # Convert to FHIR format
    fhir_patient = FHIRPatientConverter.db_to_fhir(db_patient)
    
    # Return as JSON
    return fhir_patient.dict(exclude_none=True)


@router.get("/", response_model=dict, status_code=status.HTTP_200_OK)
async def search_fhir_patients(
    identifier: Optional[str] = Query(None, description="Patient identifier"),
    email: Optional[str] = Query(None, description="Patient email"),
    name: Optional[str] = Query(None, description="Patient name"),
    _count: int = Query(10, ge=1, le=100, description="Number of results per page"),
    _offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for patients in FHIR R4 format.
    
    Returns a FHIR Bundle containing Patient resources matching the search criteria.
    """
    # Build search query
    patients = []
    
    if identifier:
        # Search by patient_id
        patient = await get_patient(db, identifier)
        if patient:
            patients = [patient]
    elif email:
        # Search by email
        patient = await get_patient_by_email(db, email)
        if patient:
            patients = [patient]
    elif name:
        # Search by name (basic implementation)
        all_patients = await get_patients(db, skip=_offset, limit=_count)
        patients = [p for p in all_patients if name.lower() in p.full_name.lower()]
    else:
        # List all patients with pagination
        patients = await get_patients(db, skip=_offset, limit=_count)
    
    # Convert to FHIR format
    fhir_patients = [FHIRPatientConverter.db_to_fhir(p) for p in patients]
    
    # Create FHIR Bundle
    bundle_entries = []
    for fhir_patient in fhir_patients:
        entry = BundleEntry(
            fullUrl=f"{settings.SERVER_HOST}:{settings.SERVER_PORT}/fhir/Patient/{fhir_patient.id}",
            resource=fhir_patient
        )
        bundle_entries.append(entry)
    
    bundle = Bundle(
        resource_type="Bundle",
        type=BundleTypeCode("searchset"),
        total=len(fhir_patients),
        entry=bundle_entries
    )
    
    return bundle.dict(exclude_none=True)


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_fhir_patient(
    fhir_patient_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new patient from FHIR R4 Patient resource.
    
    Accepts a FHIR Patient resource and creates a patient record.
    """
    try:
        # Parse FHIR Patient resource
        fhir_patient = FHIRPatient(**fhir_patient_data)
        
        # Validate FHIR resource
        is_valid, error_message = FHIRValidator.validate_fhir_patient(fhir_patient)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid FHIR Patient resource: {error_message}"
            )
        
        # Convert FHIR to database model
        patient_data = FHIRPatientConverter.fhir_to_db(fhir_patient)
        
        # Check if email already exists
        if patient_data.get("email"):
            existing = await get_patient_by_email(db, patient_data["email"])
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Patient with this email already exists"
                )
        
        # Create patient using PatientCreate schema
        patient_create = PatientCreate(**patient_data)
        
        # Create patient in database
        db_patient = await create_patient(db, patient_create)
        
        # Convert back to FHIR format
        created_fhir_patient = FHIRPatientConverter.db_to_fhir(db_patient)
        
        # Return created FHIR resource
        return created_fhir_patient.dict(exclude_none=True)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid FHIR resource format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating patient: {str(e)}"
        )


@router.put("/{patient_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def update_fhir_patient(
    patient_id: str,
    fhir_patient_data: dict,
    current_patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a patient using FHIR R4 Patient resource.
    
    Updates an existing patient record with data from a FHIR Patient resource.
    """
    # Check if patient exists
    db_patient = await get_patient(db, patient_id)
    if not db_patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found"
        )
    
    try:
        # Parse FHIR Patient resource
        fhir_patient = FHIRPatient(**fhir_patient_data)
        
        # Validate FHIR resource
        is_valid, error_message = FHIRValidator.validate_fhir_patient(fhir_patient)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid FHIR Patient resource: {error_message}"
            )
        
        # Convert FHIR to database model
        patient_data = FHIRPatientConverter.fhir_to_db(fhir_patient)
        
        # Update patient using PatientUpdate schema
        from schemas import PatientUpdate
        patient_update = PatientUpdate(**{k: v for k, v in patient_data.items() if k != "patient_id"})
        
        # Update patient in database
        updated_patient = await update_patient(db, patient_id, patient_update)
        
        if not updated_patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with ID {patient_id} not found"
            )
        
        # Convert back to FHIR format
        updated_fhir_patient = FHIRPatientConverter.db_to_fhir(updated_patient)
        
        # Return updated FHIR resource
        return updated_fhir_patient.dict(exclude_none=True)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid FHIR resource format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating patient: {str(e)}"
        )


@router.get("/{patient_id}/_history", response_model=dict, status_code=status.HTTP_200_OK)
async def get_patient_history(
    patient_id: str,
    current_patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    """
    Get patient history in FHIR format.
    
    Returns a FHIR Bundle containing the version history of a patient.
    """
    # Get patient from database
    db_patient = await get_patient(db, patient_id)
    
    if not db_patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found"
        )
    
    # Convert to FHIR format
    fhir_patient = FHIRPatientConverter.db_to_fhir(db_patient)
    
    # Create history bundle
    bundle_entry = BundleEntry(
        fullUrl=f"{settings.SERVER_HOST}:{settings.SERVER_PORT}/fhir/Patient/{patient_id}",
        resource=fhir_patient
    )
    
    bundle = Bundle(
        resource_type="Bundle",
        type=BundleTypeCode("history"),
        total=1,
        entry=[bundle_entry]
    )
    
    return bundle.dict(exclude_none=True)

