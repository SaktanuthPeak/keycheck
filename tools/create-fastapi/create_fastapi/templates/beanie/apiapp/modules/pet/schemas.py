"""
Pet module schemas (DTOs)
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
from beanie import PydanticObjectId

from ...core.base_schemas import BaseSchema


class BasePet(BaseModel):
    """Base schema with common fields for pet"""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Name of the pet"
    )
    description: Optional[str] = Field(
        default=None, max_length=500, description="Description of the pet"
    )
    image_id: Optional[PydanticObjectId] = Field(
        default=None, description="GridFS ID of the pet image"
    )
    is_active: bool = Field(default=True, description="Indicates if the pet is active")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )


class CreatePet(BaseModel):
    """Schema for creating a new pet"""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Name of the pet"
    )
    description: Optional[str] = Field(
        default=None, max_length=500, description="Description of the pet"
    )
    owner_id: PydanticObjectId = Field(
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
    owner_id: Optional[PydanticObjectId] = Field(
        default=None, description="ID of the owner (User) to update"
    )


class PetResponse(BaseSchema, BasePet):
    """Response schema for pet"""
    owner_id: PydanticObjectId = Field(
        default=None, description="ID of the owner of the pet"
    )
    owner_name: Optional[str] = Field(
        default=None, description="Name of the owner"
    )
    owner_username: Optional[str] = Field(
        default=None, description="Username of the owner"
    )

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        """Override validation to easily extract owner ID if it comes from a Link object or projection string"""
        if isinstance(obj, dict):
            # Extract owner ID from dictionary data if needed
            owner = obj.get("owner")
            # If owner is present as a dict or object with an id (e.g. from Link)
            if owner:
                if isinstance(owner, dict) and "_id" in owner:
                    obj["owner_id"] = owner["_id"]
                    obj["owner_name"] = owner.get("name")
                    obj["owner_username"] = owner.get("username")
                elif isinstance(owner, dict) and "id" in owner:
                    obj["owner_id"] = owner["id"]
                    obj["owner_name"] = owner.get("name")
                    obj["owner_username"] = owner.get("username")
                elif hasattr(owner, "id"):
                    obj["owner_id"] = owner.id
                    if hasattr(owner, "name"):
                        obj["owner_name"] = owner.name
                    if hasattr(owner, "username"):
                        obj["owner_username"] = owner.username
                elif hasattr(owner, "ref") and hasattr(owner.ref, "id"): # beanie Link
                    obj["owner_id"] = owner.ref.id
                else:
                    obj["owner_id"] = owner
        
        return super().model_validate(obj, *args, **kwargs)


class PetListProjection(BaseSchema, BasePet):
    """
    Schema for Projection (Example to avoid fetch_links=True)
    By fetching a projection, Beanie skips grabbing linked documents and fetches 
    only specific fields, solving the N+1 and performance problems.
    """
    owner_id: Optional[PydanticObjectId] = Field(default=None)

    class Settings:
        # Define the projection query for MongoDB.
        # 1 means include the field. 
        # Example for extracting an ID from a Document Link: "owner_id": "$owner.$id"
        projection = {
            "name": 1,
            "description": 1,
            "image_id": 1,
            "is_active": 1,
            "created_at": 1,
            "owner_id": "$owner.$id"  # <-- ดึงแค่ ID ของ Link แบบตรงๆ แทนที่จะใช้ fetch_links=True!
        }