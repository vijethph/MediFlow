"""Patient API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from typing import List
from prometheus_client import Counter, Histogram, Gauge
from datetime import timedelta

from database import get_db
from schemas import (
    Patient,
    PatientCreate,
    PatientUpdate,
    PatientLogin,
    Token,
    TokenData,
    HealthCheck
)
from crud import (
    create_patient,
    get_patient,
    get_patient_by_email,
    get_patients,
    update_patient,
    delete_patient,
    count_active_patients
)
from auth.auth_handler import create_access_token
from auth.auth_bearer import get_current_patient
from config import settings

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])

# Prometheus metrics
request_count = Counter(
    'patient_service_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'patient_service_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

active_patients_gauge = Gauge(
    'patient_service_active_patients',
    'Number of active patients'
)


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_patient(
    patient: PatientCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new patient.
    
    Creates a new patient record and returns a JWT token for authentication.
    """
    try:
        # Check if email already exists
        existing = await get_patient_by_email(db, patient.email)
        if existing:
            request_count.labels(method='POST', endpoint='/register', status='409').inc()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Create patient
        db_patient = await create_patient(db, patient)
        
        # Generate JWT token
        access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"patient_id": db_patient.patient_id, "email": db_patient.email},
            expires_delta=access_token_expires
        )
        
        # Update metrics
        request_count.labels(method='POST', endpoint='/register', status='201').inc()
        active_patients_gauge.inc()
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            patient_id=db_patient.patient_id,
            email=db_patient.email
        )
    except IntegrityError:
        request_count.labels(method='POST', endpoint='/register', status='409').inc()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    except Exception as e:
        request_count.labels(method='POST', endpoint='/register', status='500').inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/login", response_model=Token)
async def login_patient(
    login: PatientLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Login patient and get JWT token.
    
    For now, this just verifies the email exists and returns a token.
    In production, you would verify a password here.
    """
    db_patient = await get_patient_by_email(db, login.email)
    
    if not db_patient:
        request_count.labels(method='POST', endpoint='/login', status='404').inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    if not db_patient.is_active:
        request_count.labels(method='POST', endpoint='/login', status='403').inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient account is inactive"
        )
    
    # Generate JWT token
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"patient_id": db_patient.patient_id, "email": db_patient.email},
        expires_delta=access_token_expires
    )
    
    request_count.labels(method='POST', endpoint='/login', status='200').inc()
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        patient_id=db_patient.patient_id,
        email=db_patient.email
    )


@router.get("/{patient_id}", response_model=Patient)
async def get_patient_by_id(
    patient_id: str,
    current_patient: TokenData = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    """
    Get patient by patient_id.
    
    Requires JWT authentication.
    """
    db_patient = await get_patient(db, patient_id)
    
    if not db_patient:
        request_count.labels(method='GET', endpoint=f'/{patient_id}', status='404').inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    request_count.labels(method='GET', endpoint=f'/{patient_id}', status='200').inc()
    return db_patient


@router.get("/", response_model=List[Patient])
async def list_patients(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_patient: TokenData = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    """
    List all active patients with pagination.
    
    Requires JWT authentication.
    """
    patients = await get_patients(db, skip=skip, limit=limit)
    request_count.labels(method='GET', endpoint='/', status='200').inc()
    return patients


@router.get("/email/{email}", response_model=Patient)
async def get_patient_by_email_endpoint(
    email: str,
    current_patient: TokenData = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    """
    Get patient by email address.
    
    Requires JWT authentication.
    """
    db_patient = await get_patient_by_email(db, email)
    
    if not db_patient:
        request_count.labels(method='GET', endpoint=f'/email/{email}', status='404').inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    request_count.labels(method='GET', endpoint=f'/email/{email}', status='200').inc()
    return db_patient


@router.put("/{patient_id}", response_model=Patient)
async def update_patient_endpoint(
    patient_id: str,
    patient_update: PatientUpdate,
    current_patient: TokenData = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    """
    Update patient information.
    
    Requires JWT authentication.
    """
    try:
        db_patient = await update_patient(db, patient_id, patient_update)
        
        if not db_patient:
            request_count.labels(method='PUT', endpoint=f'/{patient_id}', status='404').inc()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        request_count.labels(method='PUT', endpoint=f'/{patient_id}', status='200').inc()
        return db_patient
    except IntegrityError:
        request_count.labels(method='PUT', endpoint=f'/{patient_id}', status='409').inc()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    except Exception as e:
        request_count.labels(method='PUT', endpoint=f'/{patient_id}', status='500').inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient_endpoint(
    patient_id: str,
    current_patient: TokenData = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete patient (set is_active=False).
    
    Requires JWT authentication.
    """
    deleted = await delete_patient(db, patient_id)
    
    if not deleted:
        request_count.labels(method='DELETE', endpoint=f'/{patient_id}', status='404').inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    request_count.labels(method='DELETE', endpoint=f'/{patient_id}', status='204').inc()
    active_patients_gauge.dec()
    return None


@router.get("/health/check", response_model=HealthCheck)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.
    
    Checks service and database connectivity.
    """
    try:
        # Check database connectivity
        await count_active_patients(db)
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return HealthCheck(
        status="healthy" if db_status == "connected" else "unhealthy",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        database=db_status
    )

