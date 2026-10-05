"""Settings (pydantic-settings). Names follow docs/api-contract.md §4; relative paths resolve against backend/."""

import logging
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..utils.logging import InterceptHandler

# backend/ (config.py -> core -> apiapp -> backend)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def resolve_path(p: str | Path) -> Path:
    p = Path(p).expanduser()
    return (p if p.is_absolute() else PROJECT_ROOT / p).resolve()


class Settings(BaseSettings):
    # base
    APP_ENV: str = "dev"
    DEBUG: bool = False
    TITLE: str = "KeyCheck API"
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"
    DOCS_URL: str | None = "/docs"
    OPENAPI_URL: str | None = "/openapi.json"
    REDOC_URL: str | None = "/redoc"
    LOGGING_LEVEL: int = logging.INFO
    LOGGERS: tuple[str, str] = ("uvicorn.asgi", "uvicorn.access")
    DISALLOW_AGENTS: list[str] = ["zgrab", "wget"]

    # contract §4
    MONGODB_URI: str = ""
    STORAGE_ROOT: Path = Path("../var/storage")
    MODEL_BUNDLE_DIR: Path = Path("../bundles/baseline_dev_v0")
    OCR_DEVICE: str = "cpu"
    MAX_UPLOAD_BYTES: int = 15 * 1024 * 1024
    MAX_IMAGE_PIXELS: int = 24_000_000
    QUEUE_CAPACITY: int = 8
    MAX_ACTIVE_JOBS_PER_SESSION: int = 2
    IMAGE_RETENTION_HOURS: float = 24
    METADATA_RETENTION_HOURS: float = 168
    SESSION_SECRET: SecretStr
    COOKIE_SECURE: bool = False
    ALLOWED_ORIGINS: list[str] = []
    WORKER_LEASE_SECONDS: float = 120
    WORKER_MAX_RETRIES: int = 1

    # extras (not in the contract; safe defaults)
    LAYOUTS_DIR: Path = Path("../layouts")
    DEFAULT_LAYOUT_ID: str = "qwerty_stagger_letters_v1"
    MONGODB_DB: str = "keycheck"  # used when MONGODB_URI has no default database
    WORKER_POLL_SECONDS: float = 1.0
    RETENTION_INTERVAL_SECONDS: float = 300
    ORPHAN_GRACE_SECONDS: float = 600
    WORKER_AUTOSTART: bool = True  # memory mode: start the in-process worker thread in lifespan
    INSPECTION_LIST_MAX: int = 50

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("STORAGE_ROOT", "MODEL_BUNDLE_DIR", "LAYOUTS_DIR", mode="after")
    @classmethod
    def _abs_path(cls, v: Path) -> Path:
        return resolve_path(v)

    @field_validator("SESSION_SECRET", mode="after")
    @classmethod
    def _secret_len(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 16:
            raise ValueError("SESSION_SECRET must be at least 16 characters")
        return v

    @field_validator("ALLOWED_ORIGINS", mode="after")
    @classmethod
    def _strip_origins(cls, v: list[str]) -> list[str]:
        return [o.rstrip("/").lower() for o in v if o]

    @property
    def memory_mode(self) -> bool:
        return not self.MONGODB_URI

    @property
    def api_v1(self) -> str:
        return f"{self.API_PREFIX}/v1"

    @property
    def heartbeat_seconds(self) -> float:
        return max(0.2, self.WORKER_LEASE_SECONDS / 4)

    @property
    def fastapi_kwargs(self) -> dict[str, Any]:
        return {
            "debug": self.DEBUG,
            "docs_url": self.DOCS_URL,
            "openapi_url": self.OPENAPI_URL,
            "redoc_url": self.REDOC_URL,
            "title": self.TITLE,
            "version": self.VERSION,
        }

    def configure_logging(self) -> None:
        logging.getLogger().handlers = [InterceptHandler()]
        for logger_name in self.LOGGERS:
            logging.getLogger(logger_name).handlers = [InterceptHandler(level=self.LOGGING_LEVEL)]
        logger.configure(handlers=[{"sink": sys.stderr, "level": self.LOGGING_LEVEL}])


@lru_cache
def get_settings() -> Settings:
    return Settings()
