"""Reject oversized upload bodies while they stream in (before multipart parsing finishes)."""

from fastapi import FastAPI
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ..core.config import Settings
from ..core.errors import AppError, ErrorCode, error_response

MULTIPART_OVERHEAD = 64 * 1024


class UploadBodyLimit:
    def __init__(self, app: ASGIApp, path: str, max_body: int) -> None:
        self.app = app
        self.path = path
        self.max_body = max_body

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"].rstrip("/") != self.path:
            await self.app(scope, receive, send)
            return
        for k, v in scope.get("headers", []):
            if k == b"content-length":
                try:
                    too_big = int(v) > self.max_body
                except ValueError:
                    too_big = False
                if too_big:
                    await error_response(ErrorCode.IMAGE_TOO_LARGE)(scope, receive, send)
                    return
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body:
                    raise AppError(ErrorCode.IMAGE_TOO_LARGE)
            return message

        await self.app(scope, limited_receive, send)


def init_body_limit_middleware(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(UploadBodyLimit, path=f"{settings.api_v1}/uploads",
                       max_body=settings.MAX_UPLOAD_BYTES + MULTIPART_OVERHEAD)
