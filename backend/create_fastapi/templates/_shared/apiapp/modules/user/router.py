"""
User API router - REST endpoints for user management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page, Params

from .use_case import UserUseCase, get_user_use_case
from .schemas import CreateUser, GetUser, UpdateUser, UpdateUserPassword, UserResponse
from . import model
from ...core.security import get_current_user
from ...core.exceptions import DuplicatedError, ValidationError
from ..auth.schemas import Message


router = APIRouter(prefix="/v1/users", tags=["User"])


@router.get("", dependencies=[Depends(Params)], response_model=Page[UserResponse])
async def get_users(
    params: GetUser = Depends(),
    use_case: UserUseCase = Depends(get_user_use_case),
    _: dict = Depends(get_current_user),
):
    """Get paginated list of users with optional filters."""
    return await use_case.search(
        query=params.search,
        role=params.role.value if params.role else None,
        is_active=params.is_active,
    )


@router.post(
    "/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse
)
async def register_user(
    data: CreateUser,
    use_case: UserUseCase = Depends(get_user_use_case),
):
    """Register a new user."""
    try:
        return await use_case.create(data)
    except (DuplicatedError, ValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: model.User = Depends(get_current_user),
):
    """Get current authenticated user's profile."""
    return UserResponse.model_validate(current_user.model_dump())


@router.patch("/me/password", response_model=Message)
async def update_current_user_password(
    data: UpdateUserPassword,
    current_user: model.User = Depends(get_current_user),
    use_case: UserUseCase = Depends(get_user_use_case),
):
    """Change password for the current user and revoke all existing tokens."""
    try:
        updated = await use_case.update_password(str(current_user.id), data)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return Message(detail="Password updated successfully")


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    use_case: UserUseCase = Depends(get_user_use_case),
    _: dict = Depends(get_current_user),
):
    """Get user by ID."""
    user = await use_case.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    data: UpdateUser,
    use_case: UserUseCase = Depends(get_user_use_case),
    _: dict = Depends(get_current_user),
):
    """Update user by ID."""
    try:
        user = await use_case.update(user_id, data)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user
    except (DuplicatedError, ValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    use_case: UserUseCase = Depends(get_user_use_case),
    _: dict = Depends(get_current_user),
):
    """Delete user by ID."""
    deleted = await use_case.delete(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
