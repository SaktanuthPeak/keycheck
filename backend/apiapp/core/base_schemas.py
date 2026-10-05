"""
Base schemas for the application
"""

from datetime import UTC, datetime
from typing import TypeVar

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

T = TypeVar("T", bound="BaseSchema")


class BaseSchema(BaseModel):
    id: PydanticObjectId | str | None = Field(default=None)


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""

    created_at: datetime
    updated_at: datetime | None = None


class ErrorResponse(BaseModel):
    """Standard error response"""

    detail: str
    code: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SuccessResponse(BaseModel):
    """Standard success response"""

    message: str
    data: dict | None = None
