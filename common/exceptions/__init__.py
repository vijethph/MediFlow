"""Common custom exceptions."""

from common.exceptions.custom_exceptions import (
    HealthcareException,
    PatientNotFoundError,
    AppointmentNotFoundError,
    InvoiceNotFoundError,
    PaymentNotFoundError,
    ClaimNotFoundError,
    ValidationError,
    DuplicateResourceError,
    ServiceUnavailableError,
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
    InvalidStatusTransitionError,
    PaymentProcessingError,
    ResourceNotFoundError, 
)

__all__ = [
    "HealthcareException",
    "PatientNotFoundError",
    "AppointmentNotFoundError",
    "InvoiceNotFoundError",
    "PaymentNotFoundError",
    "ClaimNotFoundError",
    "ValidationError",
    "DuplicateResourceError",
    "ServiceUnavailableError",
    "AuthenticationError",
    "AuthorizationError",
    "DatabaseError",
    "InvalidStatusTransitionError",
    "PaymentProcessingError",
    "ResourceNotFoundError",
]
