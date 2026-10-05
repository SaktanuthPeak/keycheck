"""Worker status (heartbeat) and model bundle registry: in-memory and MongoDB implementations."""

import threading
from datetime import datetime, timedelta
from typing import Protocol

from .model import ModelBundleDoc, ModelBundleRecord, WorkerHeartbeatDoc, WorkerStatus


class WorkerStatusRepo(Protocol):
    async def put(self, status: WorkerStatus) -> None: ...

    async def latest(self) -> WorkerStatus | None: ...

    async def prune(self, before: datetime) -> None: ...


class ModelBundleRepo(Protocol):
    async def register_active(self, rec: ModelBundleRecord) -> None: ...

    async def active(self) -> ModelBundleRecord | None: ...


class MemoryWorkerStatusRepo:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, WorkerStatus] = {}

    async def put(self, status: WorkerStatus) -> None:
        with self._lock:
            self._items[status.worker_id] = status.model_copy()

    async def latest(self) -> WorkerStatus | None:
        with self._lock:
            return max(self._items.values(), key=lambda s: s.heartbeat_at, default=None)

    async def prune(self, before: datetime) -> None:
        with self._lock:
            self._items = {k: v for k, v in self._items.items() if v.heartbeat_at >= before}


class MemoryModelBundleRepo:
    def __init__(self) -> None:
        self._active: ModelBundleRecord | None = None

    async def register_active(self, rec: ModelBundleRecord) -> None:
        self._active = rec.model_copy(update={"active": True})

    async def active(self) -> ModelBundleRecord | None:
        return self._active


class MongoWorkerStatusRepo:
    @property
    def col(self):
        return WorkerHeartbeatDoc.get_pymongo_collection()

    async def put(self, status: WorkerStatus) -> None:
        await self.col.update_one({"worker_id": status.worker_id}, {"$set": status.model_dump()}, upsert=True)

    async def latest(self) -> WorkerStatus | None:
        d = await self.col.find_one({}, sort=[("heartbeat_at", -1)])
        if d is None:
            return None
        d.pop("_id", None)
        return WorkerStatus.model_validate(d)

    async def prune(self, before: datetime) -> None:
        await self.col.delete_many({"heartbeat_at": {"$lt": before}})


class MongoModelBundleRepo:
    @property
    def col(self):
        return ModelBundleDoc.get_pymongo_collection()

    async def register_active(self, rec: ModelBundleRecord) -> None:
        await self.col.update_one({"bundle_id": rec.bundle_id}, {"$set": {**rec.model_dump(), "active": True}},
                                  upsert=True)
        await self.col.update_many({"bundle_id": {"$ne": rec.bundle_id}}, {"$set": {"active": False}})

    async def active(self) -> ModelBundleRecord | None:
        d = await self.col.find_one({"active": True})
        if d is None:
            return None
        d.pop("_id", None)
        return ModelBundleRecord.model_validate(d)


def is_fresh(status: WorkerStatus | None, now: datetime, heartbeat_seconds: float) -> bool:
    return status is not None and status.heartbeat_at >= now - timedelta(seconds=3 * heartbeat_seconds + 5)
