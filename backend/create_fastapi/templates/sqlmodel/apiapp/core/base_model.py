import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlmodel import SQLModel, Field

class BaseSQLModel(SQLModel):
    """
    Abstract base class for all SQLModel models.
    Provides standard PostgreSQL best practices for primary keys and timestamps.
    """
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        sa_type=UUID(as_uuid=True)
    )
    created_at: Optional[datetime] = Field(
        default=None,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "server_default": text("TIMEZONE('utc', CURRENT_TIMESTAMP)"),
            "nullable": False
        }
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "onupdate": text("TIMEZONE('utc', CURRENT_TIMESTAMP)"),
            "nullable": True
        }
    )
