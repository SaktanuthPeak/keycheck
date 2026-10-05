"""Integration test harness (Spec §16.2). Every test using `env`/`make_env` runs twice:
memory mode (worker thread inside the API) and MongoDB mode (worker as a separate asyncio task, same as the
worker process). MongoDB tests use TEST_MONGODB_URI (default mongodb://localhost:27018/keycheck_test) and are
skipped when it is unreachable:  docker run -d --rm --name keycheck-mongo-test -p 27018:27017 mongo:8.2.4
"""

import asyncio
import functools
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from pymongo import MongoClient

from apiapp.core.config import Settings
from apiapp.run import create_app
from apiapp.worker.runner import InspectionWorker

from .fakes import GOOD_POINTS, LAYOUT_ID, LAYOUTS_DIR, FakeInspector, image_bytes

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
MONGO_URI = os.environ.get("TEST_MONGODB_URI", "mongodb://localhost:27018/keycheck_test")
TERMINAL = ("completed", "rejected", "failed")


@functools.cache
def mongo_available() -> bool:
    try:
        with MongoClient(MONGO_URI, serverSelectionTimeoutMS=800) as c:
            c.admin.command("ping")
        return True
    except Exception:
        return False


def drop_mongo_db() -> None:
    with MongoClient(MONGO_URI) as c:
        c.drop_database(c.get_default_database().name)


class Env:
    def __init__(self, app, settings: Settings, fake: FakeInspector, mode: str) -> None:
        self.app = app
        self.settings = settings
        self.fake = fake
        self.mode = mode
        self._clients: list[AsyncClient] = []
        self._workers: list[tuple[threading.Event, asyncio.Task]] = []

    @property
    def container(self):
        return self.app.state.container

    @property
    def images_dir(self) -> Path:
        return self.settings.STORAGE_ROOT / "images"

    def files(self) -> list[str]:
        return sorted(p.name for p in self.images_dir.iterdir()) if self.images_dir.exists() else []

    def client(self, **kw) -> AsyncClient:
        """A new browser: own cookie jar, so its own session."""
        c = AsyncClient(transport=ASGITransport(app=self.app, **kw), base_url="http://test")
        self._clients.append(c)
        return c

    def start_worker(self, factory=None, worker_id: str | None = None) -> InspectionWorker:
        """Worker loop as an asyncio task in the test loop (MongoDB mode, or memory mode with autostart off)."""
        w = InspectionWorker(self.container, factory or (lambda layout_id: self.fake), worker_id=worker_id)
        stop = threading.Event()
        self._workers.append((stop, asyncio.create_task(w.run(stop))))
        return w

    async def stop_workers(self) -> None:
        for stop, _ in self._workers:
            stop.set()
        for _, task in self._workers:
            try:
                await asyncio.wait_for(task, timeout=15)
            except Exception:
                task.cancel()
        self._workers.clear()

    async def close(self) -> None:
        self.fake.release()
        await self.stop_workers()
        for c in self._clients:
            await c.aclose()

    # ---- helpers ----
    async def upload(self, client: AsyncClient, data: bytes | None = None, name: str = "photo.jpg",
                     ctype: str = "image/jpeg") -> dict:
        r = await client.post("/api/v1/uploads", files={"image": (name, data or image_bytes(), ctype)})
        assert r.status_code == 201, r.text
        return r.json()

    async def submit(self, client: AsyncClient, image_id: str, points=None, **extra):
        body = {"image_id": image_id, "layout_id": LAYOUT_ID,
                "reference_points_normalized": points or GOOD_POINTS, **extra}
        return await client.post("/api/v1/inspections", json=body)

    async def wait(self, client: AsyncClient, inspection_id: str, until=TERMINAL, timeout: float = 15) -> dict:
        loop = asyncio.get_running_loop()
        end = loop.time() + timeout
        while True:
            r = await client.get(f"/api/v1/inspections/{inspection_id}")
            assert r.status_code == 200, r.text
            body = r.json()
            if body["status"] in until:
                return body
            if loop.time() > end:
                raise AssertionError(f"inspection stuck in {body['status']}")
            await asyncio.sleep(0.05)


@pytest.fixture(params=["memory", "mongo"])
def mode(request) -> str:
    if request.param == "mongo" and not mongo_available():
        pytest.skip(f"MongoDB not reachable at {MONGO_URI}")
    return request.param


@pytest.fixture
def make_env(mode, tmp_path):
    @asynccontextmanager
    async def _make(*, fake: FakeInspector | None = None, factory=None, start_worker: bool = True, **overrides):
        fake = fake or FakeInspector()
        factory = factory or (lambda layout_id: fake)
        values = dict(
            SESSION_SECRET="test-secret-0123456789abcdef",
            STORAGE_ROOT=tmp_path / "storage",
            MODEL_BUNDLE_DIR=tmp_path / "bundle",
            LAYOUTS_DIR=LAYOUTS_DIR,
            MONGODB_URI=MONGO_URI if mode == "mongo" else "",
            WORKER_POLL_SECONDS=0.05,
            WORKER_LEASE_SECONDS=4,
            RETENTION_INTERVAL_SECONDS=3600,
            WORKER_AUTOSTART=start_worker,
            LOGGING_LEVEL=30,
        )
        values.update(overrides)
        if mode == "mongo":
            drop_mongo_db()
        settings = Settings(_env_file=None, **values)
        app = create_app(settings, inspector_factory=factory)
        env = Env(app, settings, fake, mode)
        async with LifespanManager(app, startup_timeout=30, shutdown_timeout=30):
            if mode == "mongo" and start_worker:
                env.start_worker(factory)
            try:
                yield env
            finally:
                await env.close()

    return _make


@pytest.fixture
async def env(make_env):
    async with make_env() as e:
        yield e
