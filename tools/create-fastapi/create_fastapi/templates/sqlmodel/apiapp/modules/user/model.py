"""
User SQLModel document model
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import timezone, datetime
from .schemas import BaseUser
from ...core.base_model import BaseSQLModel

from sqlalchemy import TIMESTAMP

class User(BaseUser, BaseSQLModel, table=True):
    """
    User model for PostgreSQL collection
    """
    __tablename__ = "users"
    
    username: str = Field(unique=True, index=True)
    hashed_password: str
    last_login_date: Optional[datetime] = Field(default=None, sa_type=TIMESTAMP(timezone=True))
    token_version: int = Field(default=0, ge=0)

    def __init__(self, **data):
        if "username" in data and data["username"]:
            data["username"] = data["username"].lower().strip()
        super().__init__(**data)

    def __str__(self) -> str:
        return f"User(id={self.id})"

    def set_password(self, password: str) -> None:
        """
        Set the user's password after hashing it.
        """
        import bcrypt
        self.hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt(14)).decode()

    def verify_password(self, password: str) -> bool:
        """
        Verify the provided password against the stored hashed password.
        """
        import bcrypt
        return bcrypt.checkpw(password.encode(), self.hashed_password.encode())
