"""
Attachment SQLModel document model
"""

from sqlmodel import Field
from typing import Optional
from .schemas import BaseAttachment
from ...core.base_model import BaseSQLModel


import uuid

class Attachment(BaseAttachment, BaseSQLModel, table=True):
    """
    Attachment model for PostgreSQL
    """
    __tablename__ = "attachments"

    uploaded_by_id: uuid.UUID = Field(foreign_key="users.id")

    def __str__(self) -> str:
        return f"Attachment(id={self.id})"