from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi_pagination import add_pagination

from .core.router import init_routers
from .core import http_error, validation_error
from contextlib import asynccontextmanager
from .middlewares.base import init_all_middlewares
from .infrastructure.database import init_beanie
from loguru import logger
from .core.config import get_settings
from dotenv import load_dotenv
import os
from pathlib import Path


def create_app() -> FastAPI:
    # Get project root directory (go up 2 levels from run.py)
    project_root = Path(__file__).resolve().parent.parent

    env_file = (
        ".env"
        if os.getenv("APP_ENV") == "dev"
        else ".env.prod"
        if os.getenv("APP_ENV") == "prod"
        else ".env.test"
    )
    env_path = project_root / env_file
    if not env_path.exists():
        env_path = project_root / ".env"

    # Load environment variables from correct path
    load_dotenv(env_path)
    logger.debug(f"Loading env from: {env_path}")
    logger.debug(f"APP_ENV: {os.getenv('APP_ENV')}")

    settings = get_settings()
    settings.configure_logging()

    # Debug: print settings and which fields came from environment
    def _mask_sensitive(key: str, value: object) -> str:
        try:
            s = str(value)
        except Exception:
            return "<unrepresentable>"
        if any(
            t in key.upper()
            for t in ("SECRET", "KEY", "PASSWORD", "TOKEN", "DATABASE", "URI")
        ):
            return "<sensitive>"
        return s

    try:
        all_settings = settings.model_dump()
    except Exception:
        # fallback for older pydantic versions
        all_settings = getattr(settings, "dict", lambda: {})()

    fields_set = getattr(settings, "model_fields_set", None) or getattr(
        settings, "__pydantic_fields_set__", set()
    )

    logger.debug(f"Settings loaded from: {env_path}")
    if fields_set:
        logger.debug(
            f"Fields loaded from env ({len(fields_set)}): {', '.join(sorted(fields_set))}"
        )
        for k in sorted(fields_set):
            v = _mask_sensitive(k, all_settings[k])
            logger.debug(f"{k}={v}")
    else:
        logger.debug("No fields loaded from env")

    app = FastAPI(lifespan=lifespan, **settings.fastapi_kwargs)
    app.add_exception_handler(HTTPException, http_error.http_error_handler)
    app.add_exception_handler(
        RequestValidationError, validation_error.http422_error_handler
    )
    init_all_middlewares(app, settings=settings)
    app.router.lifespan_context = lifespan

    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_beanie(settings)  # เปิด comment นี้ด้วย
    init_routers(app, settings)
    use_route_names_as_operation_ids(app)
    add_pagination(app)
    yield


def use_route_names_as_operation_ids(app: FastAPI) -> None:
    """
    Simplify operation IDs so that generated API clients have simpler function
    names.

    Should be called only after all routes have been added.
    """
    for route in app.routes:
        if hasattr(route, "operation_id"):
            route.operation_id = route.name
