"""
Auth use case - handles authentication logic
"""

import datetime

from beanie import PydanticObjectId
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..user.model import User
from .model import RevokedRefreshToken
from ...core import security
from ...core.config import settings
from . import schemas


class AuthUseCase:
    """Authentication use case"""

    async def login_for_access_token(
        self,
        form_data: OAuth2PasswordRequestForm,
    ) -> schemas.GetAccessTokenResponse:
        """Get access token (simple OAuth2 flow)"""
        user = await User.find_one({"username": form_data.username, "is_active": True})

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.verify_password(form_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = datetime.timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        access_token = security.jwt_handler.create_access_token(
            data={
                "sub": str(user.id),
                "token_type": "access",
                "ver": user.token_version,
            },
            expires_delta=access_token_expires,
        )
        return schemas.GetAccessTokenResponse(
            access_token=access_token, token_type="bearer"
        )

    async def authenticate(
        self,
        form_data: schemas.SignIn,
    ) -> schemas.Token:
        """Full authentication with access + refresh tokens"""
        user = await User.find_one({"username": form_data.username, "is_active": True})

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )

        if not user.verify_password(form_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )

        # Update last login
        user.last_login_date = datetime.datetime.now(datetime.timezone.utc)
        await user.save()

        # Generate tokens (access: sub/type/ver; refresh: sub/type/ver/jti)
        access_token_expires = datetime.timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        refresh_token_expires = datetime.timedelta(
            minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
        )
        token_claims = {
            "sub": str(user.id),
            "ver": user.token_version,
        }

        return schemas.Token(
            access_token=security.jwt_handler.create_access_token(
                data={**token_claims, "token_type": "access"},
                expires_delta=access_token_expires,
            ),
            refresh_token=security.jwt_handler.create_refresh_token(
                data={**token_claims, "token_type": "refresh"},
                expires_delta=refresh_token_expires,
            ),
            token_type="Bearer",
            scope="",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            expires_at=datetime.datetime.now(datetime.timezone.utc) + access_token_expires,
            issued_at=user.last_login_date,
        )

    async def _get_user_by_sub(self, user_id: str) -> User:
        try:
            user = await User.get(PydanticObjectId(user_id))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token subject",
            )
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        return user

    async def _is_refresh_revoked(self, jti: str) -> bool:
        jti_hash = security.hash_jti(jti)
        existing = await RevokedRefreshToken.find_one({"jti_hash": jti_hash})
        return existing is not None

    async def refresh_token(
        self,
        token: str,
    ) -> schemas.GetAccessTokenResponse:
        """Refresh access token using refresh token (denylist + token_version checks)."""
        try:
            payload = security.jwt_handler.decode_token(token, token_type="refresh")
        except HTTPException:
            raise

        user_id = payload.get("sub")
        jti = payload.get("jti")
        if not user_id or not jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        if await self._is_refresh_revoked(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )

        user = await self._get_user_by_sub(user_id)
        token_ver = payload.get("ver")
        if token_ver is None or token_ver != user.token_version:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )

        new_access_token = security.jwt_handler.refresh_token(
            token, token_version=user.token_version
        )
        return schemas.GetAccessTokenResponse(
            access_token=new_access_token, token_type="bearer"
        )

    async def revoke_refresh(self, token: str) -> None:
        """Denylist a refresh token by hashing its jti (best-effort for invalid tokens)."""
        try:
            payload = security.jwt_handler.decode_token(token, token_type="refresh")
        except HTTPException:
            return

        jti = payload.get("jti")
        user_id = payload.get("sub")
        exp = payload.get("exp")
        if not jti or not user_id or exp is None:
            return

        if await self._is_refresh_revoked(jti):
            return

        try:
            parsed_user_id = PydanticObjectId(user_id)
        except Exception:
            return

        expires_at = datetime.datetime.fromtimestamp(
            exp, tz=datetime.timezone.utc
        )
        entry = RevokedRefreshToken(
            jti_hash=security.hash_jti(jti),
            user_id=parsed_user_id,
            expires_at=expires_at,
        )
        await entry.insert()

    async def logout_all(self, user: User) -> None:
        """Bump token_version so all existing access/refresh tokens fail verification."""
        user.token_version += 1
        user.updated_at = datetime.datetime.now(datetime.timezone.utc)
        await user.save()

    async def logout(self) -> None:
        """Legacy no-op; prefer revoke_refresh via the logout router."""
        pass


def get_auth_use_case() -> AuthUseCase:
    """Get AuthUseCase instance"""
    return AuthUseCase()
