"""Anonymous server-issued session (Spec §13): random token in the `kc_session` HttpOnly cookie, only
HMAC-SHA256(SESSION_SECRET, token) is stored (`owner_session_hash`).
Also the Origin check for state-changing requests."""

import hashlib
import hmac
import re
import secrets
from urllib.parse import urlsplit

from fastapi import Request
from starlette.datastructures import MutableHeaders
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .config import Settings
from .errors import ErrorCode, error_response

COOKIE_NAME = "kc_session"
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")  # secrets.token_urlsafe(32)
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def hash_token(secret: str, token: str) -> str:
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def same_owner(a: str | None, b: str | None) -> bool:
    return a is not None and b is not None and hmac.compare_digest(a, b)


def origin_allowed(origin: str | None, host: str | None, allowed: list[str]) -> bool:
    """Missing Origin = non-browser client (allowed). Otherwise same-origin (Origin host == Host) or ALLOWED_ORIGINS."""
    if origin is None:
        return True
    o = origin.strip().rstrip("/").lower()
    if o in allowed:
        return True
    if o == "null":
        return False
    netloc = urlsplit(o).netloc
    return bool(netloc) and host is not None and netloc == host.strip().lower()


class SessionMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.secret = settings.SESSION_SECRET.get_secret_value()
        self.allowed = settings.ALLOWED_ORIGINS
        self.secure = settings.COOKIE_SECURE
        self.max_age = int(settings.METADATA_RETENTION_HOURS * 3600)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        if scope["method"] in UNSAFE_METHODS and not origin_allowed(
            request.headers.get("origin"), request.headers.get("host"), self.allowed
        ):
            await error_response(ErrorCode.ORIGIN_FORBIDDEN)(scope, receive, send)
            return

        token = request.cookies.get(COOKIE_NAME)
        issued = None
        if not token or not _TOKEN_RE.match(token):
            token = issued = secrets.token_urlsafe(32)
        scope.setdefault("state", {})["owner_hash"] = hash_token(self.secret, token)
        if issued is None:
            await self.app(scope, receive, send)
            return

        cookie = self._cookie_header(issued)

        async def send_with_cookie(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).append("set-cookie", cookie)
            await send(message)

        await self.app(scope, receive, send_with_cookie)

    def _cookie_header(self, token: str) -> str:
        r = Response()
        r.set_cookie(COOKIE_NAME, token, max_age=self.max_age, path="/", secure=self.secure, httponly=True,
                     samesite="lax")
        return r.headers["set-cookie"]


def get_owner(request: Request) -> str:
    """Dependency: owner_session_hash of the caller (set by SessionMiddleware)."""
    return request.state.owner_hash
