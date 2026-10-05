"""`python -m apiapp.worker` (scripts/run-worker): the separate inference worker process for MongoDB mode (W6)."""

import asyncio
import signal
import sys
import threading

from loguru import logger

from ..container import build_container
from ..core.config import get_settings
from .inspector import default_inspector_factory
from .runner import InspectionWorker


async def main() -> int:
    settings = get_settings()
    settings.configure_logging()
    if settings.memory_mode:
        logger.error("run-worker needs MONGODB_URI; in memory mode the worker runs inside the API process")
        return 2
    container = await build_container(settings, seed_layouts=False)
    stop = threading.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    try:
        await InspectionWorker(container, default_inspector_factory(settings)).run(stop)
    finally:
        await container.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
