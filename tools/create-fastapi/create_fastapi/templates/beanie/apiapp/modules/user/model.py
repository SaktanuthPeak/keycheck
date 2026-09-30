"""
User Beanie document model
"""

from beanie import Document, Indexed
from pydantic import Field, field_validator
from typing import Annotated, Optional
from datetime import UTC, datetime
import bcrypt

from .schemas import BaseUser
from ...core.base_schemas import TimestampMixin


class User(BaseUser, TimestampMixin, Document):
    """
    User document model for MongoDB collection
    """

    username: Annotated[str, Indexed(unique=True)]
    hashed_password: str
    token_version: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = None

    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        """Normalize username to lowercase for case-insensitive uniqueness"""
        return v.lower().strip() if v else v

    def __str__(self) -> str:
        return f"User(id={self.id})"

    def set_password(self, password: str) -> None:
        """
        Set the user's password after hashing it with bcrypt.
        """
        self.hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt(14)).decode()

    def verify_password(self, password: str) -> bool:
        """
        Verify the provided password against stored hashed password.
        """
        return bcrypt.checkpw(password.encode(), self.hashed_password.encode())

    class Settings:
        name = "users"
