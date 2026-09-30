import datetime
import typing as t
from enum import Enum

from pydantic import BaseModel, Field

from ...core.base_schemas import BaseSchema


class Strategy(str, Enum):
    COOKIES = "cookies"
    JWT = "jwt"


class Token(BaseModel):
    access_token: str
    refresh_token: t.Optional[str] = None
    token_type: str
    expires_in: int
    expires_at: datetime.datetime
    scope: str
    issued_at: datetime.datetime


class TokenData(BaseModel):
    user_id: str | None = None


class SignIn(BaseModel):
    username: str
    password: str
    strategy: Strategy = Strategy.JWT


class Payload(BaseSchema):
    roles: t.List[str]


class AccessTokenResponse(BaseSchema):
    access_token: str
    access_token_expires: datetime.datetime
    refresh_token: str
    refresh_token_expires: datetime.datetime


class SignInResponse(AccessTokenResponse):
    # user_info: LoginUserResponse
    access_token_expires_in: int
    ...


class RefreshToken(BaseSchema):
    grant_type: str
    refresh_token: str


class GetAccessTokenResponse(BaseModel):
    access_token: str
    token_type: str


class Message(BaseModel):
    detail: str
