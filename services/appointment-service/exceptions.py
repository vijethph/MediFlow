"""Custom exceptions for Appointment Management Service."""
from fastapi import HTTPException, status


class AppointmentNotFoundError(HTTPException):
    """Exception raised when appointment is not found."""
    
    def __init__(self, appointment_id: str = None):
        detail = "Appointment not found"
        if appointment_id:
            detail = f"Appointment with ID {appointment_id} not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class AppointmentConflictError(HTTPException):
    """Exception raised when appointment conflicts with existing appointment."""
    
    def __init__(self, detail: str = "Appointment conflict detected"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class DoctorNotAvailableError(HTTPException):
    """Exception raised when doctor is not available."""
    
    def __init__(self, detail: str = "Doctor is not available at the requested time"):
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


class ValidationError(HTTPException):
    """Exception raised for validation errors."""
    
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

