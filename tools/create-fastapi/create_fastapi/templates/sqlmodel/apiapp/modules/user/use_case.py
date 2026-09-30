"""
User use case - business logic and data access
Simplified pattern using BaseUseCase for common CRUD operations
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlmodel import select, or_
from fastapi import Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt

from .model import User
from .schemas import CreateUser, UpdateUser, UpdateUserPassword, UserResponse, UserRole
from ...core.base_use_case import BaseUseCase
from ...core.exceptions import DuplicatedError, ValidationError
from ...infrastructure.database import get_db_session

class UserUseCase(BaseUseCase[User, CreateUser, UpdateUser, UserResponse]):
    """
    User use case handling both business logic and data access.
    Inherits common CRUD operations from BaseUseCase and adds user-specific logic.
    """

    model = User
    response_schema = UserResponse

    # ==================== Create Operations (Override) ====================

    async def create(self, data: CreateUser) -> UserResponse:
        """Register a new user with validation"""
        # Validate uniqueness
        await self._validate_unique_username(data.username)
        if data.email:
            await self._validate_unique_email(data.email)

        # Create user with hashed password
        hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt(14)).decode()
        
        user = User(
            id=uuid.uuid4(),
            username=data.username,
            name=data.name,
            email=data.email,
            hashed_password=hashed,
            role=UserRole(data.role) if isinstance(data.role, str) else data.role,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return self._to_response(user)

    # ==================== Read Operations (Custom) ====================

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username (returns model for auth)"""
        statement = select(User).where(User.username == username.lower().strip())
        result = await self.session.exec(statement)
        return result.first()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        statement = select(User).where(User.email == email)
        result = await self.session.exec(statement)
        return result.first()

    async def search(
        self,
        query: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Page[UserResponse]:
        """Search users with filters and pagination"""
        find_query = select(User)
        
        if query and query.strip():
            find_query = find_query.where(
                or_(
                    User.username.ilike(f"%{query}%"),
                    User.email.ilike(f"%{query}%"),
                    User.name.ilike(f"%{query}%")
                )
            )

        if role:
            find_query = find_query.where(User.role == role)

        if is_active is not None:
            find_query = find_query.where(User.is_active == is_active)

        find_query = find_query.order_by(User.created_at.desc())

        # Paginate and convert to response
        return await paginate(self.session, find_query, transformer=self._page_to_response_transformer)

    # ==================== Update Operations (Override) ====================

    async def update(self, user_id: str, data: UpdateUser) -> Optional[UserResponse]:
        """Update user with validation"""
        try:
            parsed_id = uuid.UUID(user_id)
        except ValueError:
            return None
            
        user = await self.session.get(User, parsed_id)
        if not user:
            return None

        update_data = data.model_dump(exclude_unset=True, exclude_none=True)

        # Validate username uniqueness if changing
        if "username" in update_data and update_data["username"] != user.username:
            await self._validate_unique_username(
                update_data["username"], exclude_id=user.id
            )

        # Update fields
        for key, value in update_data.items():
            setattr(user, key, value)

        user.updated_at = datetime.now(timezone.utc)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        return self._to_response(user)

    async def update_password(
        self, user_id: str, data: UpdateUserPassword
    ) -> bool:
        """Verify old password, set new hash, and bump token_version (revokes all tokens)."""
        try:
            parsed_id = uuid.UUID(user_id)
        except ValueError:
            return False

        user = await self.session.get(User, parsed_id)
        if not user:
            return False

        if not user.verify_password(data.old_password):
            raise ValidationError("Incorrect current password")

        user.set_password(data.new_password)
        user.token_version += 1
        user.updated_at = datetime.now(timezone.utc)
        self.session.add(user)
        await self.session.commit()
        return True

    async def bump_token_version(self, user_id: str) -> bool:
        """Force-logout a user by invalidating all issued tokens (admin/scripts)."""
        try:
            parsed_id = uuid.UUID(user_id)
        except ValueError:
            return False

        user = await self.session.get(User, parsed_id)
        if not user:
            return False

        user.token_version += 1
        user.updated_at = datetime.now(timezone.utc)
        self.session.add(user)
        await self.session.commit()
        return True

    # ==================== Private Helpers ====================

    async def _validate_unique_username(
        self, username: str, exclude_id: Optional[uuid.UUID] = None
    ) -> None:
        """Validate username is unique"""
        statement = select(User).where(User.username == username.lower().strip())
        if exclude_id:
            statement = statement.where(User.id != exclude_id)

        result = await self.session.exec(statement)
        existing = result.first()
        
        if existing:
            raise DuplicatedError("Username already exists")

    async def _validate_unique_email(
        self, email: str, exclude_id: Optional[uuid.UUID] = None
    ) -> None:
        """Validate email is unique"""
        statement = select(User).where(User.email == email)
        if exclude_id:
            statement = statement.where(User.id != exclude_id)

        result = await self.session.exec(statement)
        existing = result.first()
        
        if existing:
            raise DuplicatedError("Email already exists")


# Dependency injection
def get_user_use_case(session: AsyncSession = Depends(get_db_session)) -> UserUseCase:
    """Get UserUseCase instance"""
    return UserUseCase(session)
