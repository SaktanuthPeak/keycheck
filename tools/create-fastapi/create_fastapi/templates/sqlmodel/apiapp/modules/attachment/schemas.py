"""
Attachment module schemas (DTOs)
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

from ...core.base_schemas import BaseSchema


import uuid

class BaseAttachment(BaseModel):
    """Base schema with common fields for attachment"""

    filename: str = Field(..., description="Original filename of the attachment")
    file_id: str = Field(..., description="Storage name/UUID inside uploads directory")
    content_type: str = Field(..., description="MIME type of the attachment")
    size_bytes: int = Field(..., description="Size of the attachment in bytes")
    uploaded_by_id: uuid.UUID = Field(..., description="UUID of the user who uploaded the attachment")


class CreateAttachment(BaseModel):
    """Schema for creating a new attachment"""
    filename: str
    file_id: str
    content_type: str
    size_bytes: int
    uploaded_by_id: uuid.UUID


class UpdateAttachment(BaseModel):
    """Schema for updating attachment data - all fields optional"""
    filename: Optional[str] = None
    file_id: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None


class AttachmentResponse(BaseSchema, BaseAttachment):
    """Response schema for attachment"""
    pass