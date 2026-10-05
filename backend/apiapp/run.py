import asyncio
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi_pagination import add_pagination
from loguru import logger

from .container import build_container
from .core.config import Settings, get_settings
from .core.errors import install_error_handlers
from .core.router import init_routers
from .middlewares.base import init_all_middlewares


def create_app(settings: Settings | None = None, *, inspector_factory=None) -> FastAPI:
    """`inspector_factory(layout_id)` overrides the real ai.inference.Inspector (tests use a fake)."""
    settings = settings or get_settings()
    settings.configure_logging()
    logger.debug(f"APP_ENV={settings.APP_ENV} mode={'memory' if settings.memory_mode else 'mongodb'}")

    app = FastAPI(lifespan=lifespan, **settings.fastapi_kwargs)
    app.state.settings = settings
    app.state.inspector_factory = inspector_factory
    install_error_handlers(app)
    init_all_middlewares(app, settings=settings)
    init_routers(app, settings)
    use_route_names_as_operation_ids(app)
    add_pagination(app)
    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    container = await build_container(settings)
    app.state.container = container
    stop = threading.Event()
    thread = None
    if settings.memory_mode and settings.WORKER_AUTOSTART:
        thread = start_worker_thread(app, stop)
    try:
        yield
    finally:
        stop.set()
        if thread is not None:
            thread.join(timeout=settings.WORKER_POLL_SECONDS + 10)
        await container.close()


def start_worker_thread(app: FastAPI, stop: threading.Event) -> threading.Thread:
    """Memory mode (W2): one worker thread inside the API process with its own event loop.
    Imported lazily so MongoDB mode never loads the worker (or ai.inference / paddle) into the API process."""
    from .worker.inspector import default_inspector_factory
    from .worker.runner import InspectionWorker

    container = app.state.container
    factory = app.state.inspector_factory or default_inspector_factory(container.settings)
    worker = InspectionWorker(container, factory)
    app.state.worker = worker

    def target() -> None:
        try:
            asyncio.run(worker.run(stop))
        except Exception as e:
            logger.opt(exception=e).error("worker thread crashed: {}", type(e).__name__)

    t = threading.Thread(target=target, name="keycheck-worker", daemon=True)
    t.start()
    return t


def use_route_names_as_operation_ids(app: FastAPI) -> None:
    """
    Simplify operation IDs so that generated API clients have simpler function
    names.

    Should be called only after all routes have been added.
    """
    for route in app.routes:
        if hasattr(route, "operation_id"):
            route.operation_id = route.name
