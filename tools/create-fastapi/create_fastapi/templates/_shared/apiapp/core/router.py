"""
Router initialization - auto-discovery from modules
"""

import importlib
import pkgutil
from typing import List

from fastapi import APIRouter, FastAPI
from loguru import logger

from ..core.config import Settings


def _discover_routers() -> List[tuple[str, APIRouter]]:
    """Discover all routers from modules/*/router.py"""
    routers = []
    modules_package_name = "apiapp.modules"

    try:
        modules_package = importlib.import_module(modules_package_name)

        for _, module_name, ispkg in pkgutil.iter_modules(
            modules_package.__path__, modules_package.__name__ + "."
        ):
            if not ispkg:
                continue

            try:
                router_module = importlib.import_module(f"{module_name}.router")
                if hasattr(router_module, "router"):
                    router = getattr(router_module, "router")
                    if isinstance(router, APIRouter):
                        name = module_name.split(".")[-1]
                        routers.append((name, router))
            except ImportError:
                continue

    except Exception as e:
        logger.error(f"Failed to discover routers: {e}")

    return routers


def init_routers(app: FastAPI, settings: Settings) -> None:
    """Initialize all routers from modules (auto-discovery)"""
    routers = _discover_routers()

    logger.info(f"Discovered {len(routers)} routers:")
    for name, router in routers:
        app.include_router(router, prefix=settings.API_PREFIX)
        logger.info(f"  - {name}")
