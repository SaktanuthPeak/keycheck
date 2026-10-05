from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import Settings
from ..core.session import SessionMiddleware
from .body_limit import init_body_limit_middleware
from .security import init_security_middleware
from .timing import init_timing_middleware


def init_all_middlewares(app: FastAPI, settings: Settings) -> None:
    """Initialize all application middlewares (last added = outermost)."""
    init_body_limit_middleware(app, settings)
    init_security_middleware(app, settings)
    init_timing_middleware(app, settings)
    app.add_middleware(SessionMiddleware, settings=settings)
    if settings.ALLOWED_ORIGINS:
        # Same-origin via proxy is the default (W-D3); CORS only for explicitly allowed cross origins.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["content-type"],
        )
