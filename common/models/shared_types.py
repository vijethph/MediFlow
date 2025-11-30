"""
Shared Pydantic Models and Types.

This module defines shared types used across multiple services.
"""

from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum


class Money(BaseModel):
    """
    FHIR Money Type.

    Represents a monetary amount with currency.
    """

    value: Decimal = Field(..., description="Monetary amount")
    currency: str = Field(default="USD", description="ISO 4217 Currency code")

    class Config:
        json_schema_extra = {"example": {"value": 150.00, "currency": "USD"}}


class GenderEnum(str, Enum):
    """FHIR Gender codes."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class ContactPointSystemEnum(str, Enum):
    """FHIR Contact Point System."""

    PHONE = "phone"
    FAX = "fax"
    EMAIL = "email"
    SMS = "sms"
    URL = "url"
