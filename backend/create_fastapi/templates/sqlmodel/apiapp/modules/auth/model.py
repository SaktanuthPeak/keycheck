"""
Auth SQLModel models (refresh-token denylist)
"""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP
from sqlmodel import Field

from ...core.base_model import BaseSQLModel


class RevokedRefreshToken(BaseSQLModel, table=True):
    """Persisted denylist entry for a revoked refresh token (by jti hash)."""

    __tablename__ = "revoked_refresh_tokens"

    jti_hash: str = Field(unique=True, index=True, max_length=64)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    expires_at: datetime = Field(sa_type=TIMESTAMP(timezone=True))
