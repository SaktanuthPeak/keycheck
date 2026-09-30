"""
Auth Beanie document models (refresh-token denylist)
"""

from datetime import UTC, datetime
from typing import Annotated, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field

from ...core.base_schemas import TimestampMixin


class RevokedRefreshToken(TimestampMixin, Document):
    """Persisted denylist entry for a revoked refresh token (by jti hash)."""

    jti_hash: Annotated[str, Indexed(unique=True)]
    user_id: PydanticObjectId
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = None

    class Settings:
        name = "revoked_refresh_tokens"
