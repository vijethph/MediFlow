"""FHIR-compatible Pydantic schemas."""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import date


class FHIRPatientResponse(BaseModel):
    """FHIR Patient resource response schema."""
    resourceType: str = Field(default="Patient", description="FHIR resource type")
    id: Optional[str] = Field(None, description="Patient ID")
    identifier: List[dict] = Field(default_factory=list, description="Patient identifiers")
    name: List[dict] = Field(default_factory=list, description="Patient names")
    telecom: Optional[List[dict]] = Field(None, description="Contact points")
    gender: Optional[str] = Field(None, description="Administrative gender")
    birthDate: Optional[date] = Field(None, description="Date of birth")
    address: Optional[List[dict]] = Field(None, description="Addresses")
    active: bool = Field(default=True, description="Whether patient record is active")
    extension: Optional[List[dict]] = Field(None, description="FHIR extensions")
    meta: Optional[dict] = Field(None, description="FHIR meta information")
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat() if v else None
        }


class FHIRBundleEntry(BaseModel):
    """FHIR Bundle entry schema."""
    fullUrl: Optional[str] = Field(None, description="Full URL of the resource")
    resource: dict = Field(..., description="FHIR resource")
    request: Optional[dict] = Field(None, description="Request information")


class FHIRBundle(BaseModel):
    """FHIR Bundle response schema."""
    resourceType: str = Field(default="Bundle", description="FHIR resource type")
    type: str = Field(default="searchset", description="Bundle type")
    total: int = Field(..., description="Total number of results")
    entry: List[FHIRBundleEntry] = Field(default_factory=list, description="Bundle entries")
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat() if v else None
        }

