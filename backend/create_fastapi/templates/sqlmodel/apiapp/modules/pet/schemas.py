"""
Pet module schemas (DTOs)
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import uuid

from ...core.base_schemas import BaseSchema


class BasePet(BaseModel):
    """Base schema with common fields for pet"""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Name of the pet"
    )
    description: Optional[str] = Field(
        default=None, max_length=500, description="Description of the pet"
    )
    image_id: Optional[str] = Field(
        default=None, description="Local file ID of the pet image"
    )
    is_active: bool = Field(default=True, description="Indicates if the pet is active")


class CreatePet(BaseModel):
    """Schema for creating a new pet"""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Name of the pet"
    )
    description: Optional[str] = Field(
        default=None, max_length=500, description="Description of the pet"
    )
    owner_id: uuid.UUID = Field(
        ..., description="ID of the owner (User) of the pet"
    )


class UpdatePet(BaseModel):
    """Schema for updating pet data - all fields optional"""

    name: Optional[str] = Field(
        default=None, min_length=1, max_length=100, description="Name of the pet"
    )
    description: Optional[str] = Field(
        default=None, max_length=500, description="Description of the pet"
    )
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the pet is active"
    )
    owner_id: Optional[uuid.UUID] = Field(
        default=None, description="ID of the owner (User) to update"
    )


class PetResponse(BaseSchema, BasePet):
    """Response schema for pet"""
    owner_id: Optional[uuid.UUID] = Field(
        default=None, description="ID of the owner of the pet"
    )
    owner_name: Optional[str] = Field(
        default=None, description="Name of the owner"
    )
    owner_username: Optional[str] = Field(
        default=None, description="Username of the owner"
    )