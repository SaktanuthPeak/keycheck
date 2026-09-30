"""
User use case - business logic and data access
Simplified pattern using Beanie's built-in methods directly
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any

from beanie import PydanticObjectId
from beanie.operators import And, Or
from beanie.odm.operators.find.evaluation import RegEx
from fastapi_pagination import Page
from fastapi_pagination.ext.beanie import paginate
import bcrypt

from .model import User
from .schemas import CreateUser, UpdateUser, UpdateUserPassword, UserResponse, UserRole
from ...core.base_use_case import BaseUseCase
from ...core.exceptions import DuplicatedError, ValidationError


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
            username=data.username,
            name=data.name,
            email=data.email,
            hashed_password=hashed,
            role=UserRole(data.role) if isinstance(data.role, str) else data.role,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        await user.insert()
        return self._to_response(user)

    # ==================== Read Operations (Custom) ====================

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username (returns model for auth)"""
        return await User.find_one({"username": username.lower().strip()})

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return await User.find_one({"email": email})

    async def search(
        self,
        query: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Page[UserResponse]:
        """Search users with filters and pagination"""
        filters = self._build_filters(query, role, is_active)

        if filters:
            find_query = User.find(And(*filters) if len(filters) > 1 else filters[0])
        else:
            find_query = User.find_all()

        find_query = find_query.sort("-created_at")

        # Paginate and convert to response
        page = await paginate(find_query)
        return self._page_to_response(page)

    # ==================== Update Operations (Override) ====================

    async def update(self, user_id: str, data: UpdateUser) -> Optional[UserResponse]:
        """Update user with validation"""
        user = await User.get(PydanticObjectId(user_id))
        if not user:
            return None

        update_data = data.model_dump(exclude_none=True)

        # Validate username uniqueness if changing
        if "username" in update_data and update_data["username"] != user.username:
            await self._validate_unique_username(
                update_data["username"], exclude_id=user.id
            )

        # Update fields
        for key, value in update_data.items():
            setattr(user, key, value)

        user.updated_at = datetime.now(timezone.utc)
        await user.save()

        return self._to_response(user)

    async def update_password(
        self, user_id: str, data: UpdateUserPassword
    ) -> bool:
        """Verify old password, set new hash, and bump token_version (revokes all tokens)."""
        user = await User.get(PydanticObjectId(user_id))
        if not user:
            return False

        if not user.verify_password(data.old_password):
            raise ValidationError("Incorrect current password")

        user.set_password(data.new_password)
        user.token_version += 1
        user.updated_at = datetime.now(timezone.utc)
        await user.save()
        return True

    async def bump_token_version(self, user_id: str) -> bool:
        """Force-logout a user by invalidating all issued tokens (admin/scripts)."""
        user = await User.get(PydanticObjectId(user_id))
        if not user:
            return False

        user.token_version += 1
        user.updated_at = datetime.now(timezone.utc)
        await user.save()
        return True

    # ==================== Delete Operations (Inherited from BaseUseCase) ====================
    # Uses the base delete() method

    # ==================== Private Helpers ====================

    async def _validate_unique_username(
        self, username: str, exclude_id: Optional[PydanticObjectId] = None
    ) -> None:
        """Validate username is unique"""
        filters: Dict[str, Any] = {"username": username.lower().strip()}
        if exclude_id:
            filters["_id"] = {"$ne": exclude_id}

        existing = await User.find_one(filters)
        if existing:
            raise DuplicatedError("Username already exists")

    async def _validate_unique_email(
        self, email: str, exclude_id: Optional[PydanticObjectId] = None
    ) -> None:
        """Validate email is unique"""
        filters: Dict[str, Any] = {"email": email}
        if exclude_id:
            filters["_id"] = {"$ne": exclude_id}

        existing = await User.find_one(filters)
        if existing:
            raise DuplicatedError("Email already exists")

    def _build_filters(
        self,
        query: Optional[str],
        role: Optional[str],
        is_active: Optional[bool],
    ) -> list:
        """Build search filters"""
        filters = []

        if query and query.strip():
            filters.append(
                Or(
                    RegEx(User.username, query, options="i"),
                    RegEx(User.email, query, options="i"),
                    RegEx(User.name, query, options="i"),
                )
            )

        if role:
            filters.append(User.role == role)

        if is_active is not None:
            filters.append(User.is_active == is_active)

        return filters


# Dependency injection
def get_user_use_case() -> UserUseCase:
    """Get UserUseCase instance"""
    return UserUseCase()
