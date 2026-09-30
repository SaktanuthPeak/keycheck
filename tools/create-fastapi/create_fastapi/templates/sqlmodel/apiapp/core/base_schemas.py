"""
Base schemas for the application
"""

import uuid
from pydantic import BaseModel, Field
from datetime import UTC, datetime
from typing import Optional, TypeVar, Union


T = TypeVar("T", bound="BaseSchema")


class BaseSchema(BaseModel):
    id: Optional[Union[uuid.UUID, str]] = Field(default=None)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ErrorResponse(BaseModel):
    """Standard error response"""

    detail: str
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SuccessResponse(BaseModel):
    """Standard success response"""

    message: str
    data: Optional[dict] = None
