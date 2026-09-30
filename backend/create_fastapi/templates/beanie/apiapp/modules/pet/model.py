"""
Pet Beanie document model
"""

from beanie import Document, Indexed, Link, PydanticObjectId
from pydantic import Field
from typing import Optional
from datetime import UTC, datetime
from .schemas import BasePet
from ...core.base_schemas import TimestampMixin
from ..user.model import User


class Pet(BasePet, TimestampMixin, Document):
    """
    Pet document model for MongoDB collection
    """

    # Add indexed fields here if needed
    # example: name: Annotated[str, Indexed(unique=True)]

    owner: Link[User]
    image_id: Optional[PydanticObjectId] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = None

    def __str__(self) -> str:
        return f"Pet(id={self.id})"

    class Settings:
        name = "pets"