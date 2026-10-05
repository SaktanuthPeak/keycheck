"""LayoutRepo: in-memory and MongoDB implementations."""

import threading
from typing import Protocol

from .model import LayoutDoc, LayoutRecord


class LayoutRepo(Protocol):
    async def upsert(self, rec: LayoutRecord) -> None: ...

    async def latest(self, layout_id: str) -> LayoutRecord | None: ...

    async def list_latest(self) -> list[LayoutRecord]: ...


class MemoryLayoutRepo:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[tuple[str, int], LayoutRecord] = {}

    async def upsert(self, rec: LayoutRecord) -> None:
        with self._lock:
            self._items[(rec.layout_id, rec.version)] = rec.model_copy(deep=True)

    async def latest(self, layout_id: str) -> LayoutRecord | None:
        with self._lock:
            cands = [r for (lid, _), r in self._items.items() if lid == layout_id]
        return max(cands, key=lambda r: r.version).model_copy(deep=True) if cands else None

    async def list_latest(self) -> list[LayoutRecord]:
        with self._lock:
            ids = sorted({lid for lid, _ in self._items})
        return [r for lid in ids if (r := await self.latest(lid)) is not None]


class MongoLayoutRepo:
    @property
    def col(self):
        return LayoutDoc.get_pymongo_collection()

    async def upsert(self, rec: LayoutRecord) -> None:
        await self.col.update_one({"layout_id": rec.layout_id, "version": rec.version},
                                  {"$set": rec.model_dump()}, upsert=True)

    async def latest(self, layout_id: str) -> LayoutRecord | None:
        d = await self.col.find_one({"layout_id": layout_id}, sort=[("version", -1)])
        if d is None:
            return None
        d.pop("_id", None)
        return LayoutRecord.model_validate(d)

    async def list_latest(self) -> list[LayoutRecord]:
        ids = sorted(await self.col.distinct("layout_id"))
        return [r for lid in ids if (r := await self.latest(lid)) is not None]
