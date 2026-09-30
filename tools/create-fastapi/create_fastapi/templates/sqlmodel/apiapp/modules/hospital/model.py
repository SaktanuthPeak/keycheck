"""
Hospital SQLModel document model
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import timezone, datetime
from .schemas import BaseHospital
from ...core.base_model import BaseSQLModel

from sqlalchemy import Column, String, ARRAY

class Hospital(BaseHospital, BaseSQLModel, table=True):
    """
    Hospital model for PostgreSQL collection
    """
    __tablename__ = "hospitals"

    services: list[str] = Field(
        sa_column=Column(ARRAY(String), nullable=False, server_default="{}")
    )

    def __str__(self) -> str:
        return f"Hospital(id={self.id})"