"""
Hospital module schemas (DTOs)
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

from ...core.base_schemas import BaseSchema


class BaseHospital(BaseModel):
    """Base schema with common fields for hospital"""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Name of the hospital"
    )
    address: str = Field(
        ..., description="Address of the veterinary hospital"
    )
    phone_number: str = Field(
        ..., description="Contact phone number"
    )
    services: list[str] = Field(
        default_factory=list, description="List of services offered (e.g., Surgery, X-Ray)"
    )
    capacity: int = Field(
        default=0, description="Maximum number of pet patients the hospital can admit"
    )
    is_active: bool = Field(default=True, description="Indicates if the hospital is active")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )


class CreateHospital(BaseModel):
    """Schema for creating a new hospital"""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Name of the hospital"
    )
    address: str = Field(
        ..., description="Address of the veterinary hospital"
    )
    phone_number: str = Field(
        ..., description="Contact phone number"
    )
    services: list[str] = Field(
        default_factory=list, description="List of services offered"
    )
    capacity: int = Field(
        default=0, description="Maximum number of pet patients the hospital can admit", ge=0
    )


class UpdateHospital(BaseModel):
    """Schema for updating hospital data - all fields optional"""

    name: Optional[str] = Field(
        default=None, min_length=1, max_length=100, description="Name of the hospital"
    )
    address: Optional[str] = Field(
        default=None, description="Address of the veterinary hospital"
    )
    phone_number: Optional[str] = Field(
        default=None, description="Contact phone number"
    )
    services: Optional[list[str]] = Field(
        default=None, description="List of services offered"
    )
    capacity: Optional[int] = Field(
        default=None, description="Maximum number of pet patients the hospital can admit", ge=0
    )
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the hospital is active"
    )


class HospitalResponse(BaseSchema, BaseHospital):
    """Response schema for hospital"""
    pass