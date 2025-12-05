"""
Custom Exception Classes for Healthcare System.

This module defines custom exceptions for better error handling across services.
"""

from typing import Any, Dict, Optional


class HealthcareException(Exception):
    """Base exception for healthcare system."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize healthcare exception.

        :param message: Error message
        :param status_code: HTTP status code
        :param details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class PatientNotFoundError(HealthcareException):
    """Exception raised when patient is not found."""

    def __init__(self, patient_id: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize patient not found exception.

        :param patient_id: Patient identifier
        :param details: Additional error details
        """
        message = f"Patient with ID '{patient_id}' not found"
        super().__init__(message, status_code=404, details=details)


class AppointmentNotFoundError(HealthcareException):
    """Exception raised when appointment is not found."""

    def __init__(self, appointment_id: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize appointment not found exception.

        :param appointment_id: Appointment identifier
        :param details: Additional error details
        """
        message = f"Appointment with ID '{appointment_id}' not found"
        super().__init__(message, status_code=404, details=details)


class InvoiceNotFoundError(HealthcareException):
    """Exception raised when invoice is not found."""

    def __init__(self, invoice_id: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize invoice not found exception.

        :param invoice_id: Invoice identifier
        :param details: Additional error details
        """
        message = f"Invoice with ID '{invoice_id}' not found"
        super().__init__(message, status_code=404, details=details)


class PaymentNotFoundError(HealthcareException):
    """Exception raised when payment is not found."""

    def __init__(self, payment_id: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize payment not found exception.

        :param payment_id: Payment identifier
        :param details: Additional error details
        """
        message = f"Payment with ID '{payment_id}' not found"
        super().__init__(message, status_code=404, details=details)


class ClaimNotFoundError(HealthcareException):
    """Exception raised when insurance claim is not found."""

    def __init__(self, claim_id: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize claim not found exception.

        :param claim_id: Claim identifier
        :param details: Additional error details
        """
        message = f"Insurance claim with ID '{claim_id}' not found"
        super().__init__(message, status_code=404, details=details)


class ValidationError(HealthcareException):
    """Exception raised for validation errors."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize validation exception.

        :param message: Validation error message
        :param field: Field that failed validation
        :param details: Additional error details
        """
        error_details = details or {}
        if field:
            error_details["field"] = field

        super().__init__(message, status_code=400, details=error_details)


class DuplicateResourceError(HealthcareException):
    """Exception raised when attempting to create duplicate resource."""

    def __init__(
        self,
        resource_type: str,
        identifier: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize duplicate resource exception.

        :param resource_type: Type of resource
        :param identifier: Resource identifier
        :param details: Additional error details
        """
        message = f"{resource_type} with identifier '{identifier}' already exists"
        super().__init__(message, status_code=409, details=details)


class ServiceUnavailableError(HealthcareException):
    """Exception raised when external service is unavailable."""

    def __init__(self, service_name: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize service unavailable exception.

        :param service_name: Name of unavailable service
        :param details: Additional error details
        """
        message = f"Service '{service_name}' is currently unavailable"
        super().__init__(message, status_code=503, details=details)


class AuthenticationError(HealthcareException):
    """Exception raised for authentication failures."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize authentication exception.

        :param message: Authentication error message
        :param details: Additional error details
        """
        super().__init__(message, status_code=401, details=details)


class AuthorizationError(HealthcareException):
    """Exception raised for authorization failures."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize authorization exception.

        :param message: Authorization error message
        :param details: Additional error details
        """
        super().__init__(message, status_code=403, details=details)


class DatabaseError(HealthcareException):
    """Exception raised for database operation failures."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize database exception.

        :param message: Database error message
        :param operation: Database operation that failed
        :param details: Additional error details
        """
        error_details = details or {}
        if operation:
            error_details["operation"] = operation

        super().__init__(message, status_code=500, details=error_details)


class InvalidStatusTransitionError(HealthcareException):
    """Exception raised for invalid status transitions."""

    def __init__(
        self,
        resource_type: str,
        current_status: str,
        new_status: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize invalid status transition exception.

        :param resource_type: Type of resource
        :param current_status: Current status
        :param new_status: Attempted new status
        :param details: Additional error details
        """
        message = f"Invalid status transition for {resource_type}: {current_status} -> {new_status}"
        error_details = details or {}
        error_details.update(
            {"current_status": current_status, "attempted_status": new_status}
        )
        super().__init__(message, status_code=400, details=error_details)


class PaymentProcessingError(HealthcareException):
    """Exception raised for payment processing failures."""

    def __init__(
        self,
        message: str,
        payment_method: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize payment processing exception.

        :param message: Payment error message
        :param payment_method: Payment method used
        :param details: Additional error details
        """
        error_details = details or {}
        if payment_method:
            error_details["payment_method"] = payment_method

        super().__init__(message, status_code=402, details=error_details)
        
class ResourceNotFoundError(HealthcareException):
    """Generic exception for missing resources."""

    def __init__(self, resource_type: str, identifier: str, details=None):
        message = f"{resource_type} with ID '{identifier}' not found"
        super().__init__(message, status_code=404, details=details)
