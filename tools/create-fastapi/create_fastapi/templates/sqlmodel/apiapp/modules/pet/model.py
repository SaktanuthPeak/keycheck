"""
Pet SQLModel document model
"""

import uuid
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import timezone, datetime
from .schemas import BasePet
from ...core.base_model import BaseSQLModel


class Pet(BasePet, BaseSQLModel, table=True):
    """
    Pet model for PostgreSQL collection
    """
    __tablename__ = "pets"
    
    owner_id: uuid.UUID = Field(foreign_key="users.id", ondelete="CASCADE")
    image_id: Optional[str] = None

    def __str__(self) -> str:
        return f"Pet(id={self.id})"