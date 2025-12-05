"""Custom exceptions for Patient Management Service."""
from fastapi import HTTPException, status


class PatientNotFoundError(HTTPException):
    """Exception raised when patient is not found."""
    
    def __init__(self, patient_id: str = None):
        detail = "Patient not found"
        if patient_id:
            detail = f"Patient with ID {patient_id} not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class PatientAlreadyExistsError(HTTPException):
    """Exception raised when patient already exists."""
    
    def __init__(self, email: str = None):
        detail = "Patient already exists"
        if email:
            detail = f"Patient with email {email} already exists"
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class InvalidCredentialsError(HTTPException):
    """Exception raised when credentials are invalid."""
    
    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class DatabaseError(HTTPException):
    """Exception raised for database errors."""
    
    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class ValidationError(HTTPException):
    """Exception raised for validation errors."""
    
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

