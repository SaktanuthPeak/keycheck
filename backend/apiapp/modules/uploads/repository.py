"""UploadRepo: in-memory (dict + lock, W2) and MongoDB (W6) implementations of the same interface."""

import threading
from datetime import datetime
from typing import Protocol

from pymongo import ReturnDocument

from .model import UploadDoc, UploadRecord


class UploadRepo(Protocol):
    async def insert(self, rec: UploadRecord) -> None: ...

    async def get(self, image_id: str) -> UploadRecord | None: ...

    async def acquire(self, image_id: str, owner: str, now: datetime) -> UploadRecord | None:
        """+1 reference if owned by `owner`, not expired and not past expires_at; else None (no change)."""
        ...

    async def release(self, image_id: str) -> UploadRecord | None:
        """-1 reference; returns the updated record (None if it no longer exists)."""
        ...

    async def delete_unreferenced(self, image_id: str) -> bool:
        """Delete the record only if reference_count <= 0."""
        ...

    async def mark_expired(self, image_id: str, now: datetime) -> bool: ...

    async def due_for_expiry(self, now: datetime) -> list[UploadRecord]: ...

    async def unreferenced_expired(self) -> list[UploadRecord]: ...

    async def storage_keys(self) -> set[str]: ...


class MemoryUploadRepo:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, UploadRecord] = {}

    def _copy(self, rec: UploadRecord | None) -> UploadRecord | None:
        return rec.model_copy(deep=True) if rec is not None else None

    async def insert(self, rec: UploadRecord) -> None:
        with self._lock:
            if rec.image_id in self._items:
                raise KeyError("duplicate image_id")
            self._items[rec.image_id] = rec.model_copy(deep=True)

    async def get(self, image_id: str) -> UploadRecord | None:
        with self._lock:
            return self._copy(self._items.get(image_id))

    async def acquire(self, image_id: str, owner: str, now: datetime) -> UploadRecord | None:
        with self._lock:
            rec = self._items.get(image_id)
            if rec is None or rec.owner_session_hash != owner or rec.expired or rec.expires_at <= now:
                return None
            rec.reference_count += 1
            return self._copy(rec)

    async def release(self, image_id: str) -> UploadRecord | None:
        with self._lock:
            rec = self._items.get(image_id)
            if rec is None:
                return None
            rec.reference_count -= 1
            return self._copy(rec)

    async def delete_unreferenced(self, image_id: str) -> bool:
        with self._lock:
            rec = self._items.get(image_id)
            if rec is None or rec.reference_count > 0:
                return False
            del self._items[image_id]
            return True

    async def mark_expired(self, image_id: str, now: datetime) -> bool:
        with self._lock:
            rec = self._items.get(image_id)
            if rec is None or rec.expired:
                return False
            rec.expired, rec.expired_at = True, now
            return True

    async def due_for_expiry(self, now: datetime) -> list[UploadRecord]:
        with self._lock:
            return [r.model_copy() for r in self._items.values() if not r.expired and r.expires_at <= now]

    async def unreferenced_expired(self) -> list[UploadRecord]:
        with self._lock:
            return [r.model_copy() for r in self._items.values() if r.expired and r.reference_count <= 0]

    async def storage_keys(self) -> set[str]:
        with self._lock:
            return {r.storage_key for r in self._items.values()}


def _rec(d: dict | None) -> UploadRecord | None:
    if d is None:
        return None
    d.pop("_id", None)
    d.pop("revision_id", None)
    return UploadRecord.model_validate(d)


class MongoUploadRepo:
    """Atomic single-document operations on the `uploads` collection (Beanie-initialised)."""

    @property
    def col(self):
        return UploadDoc.get_pymongo_collection()

    async def insert(self, rec: UploadRecord) -> None:
        await UploadDoc(**rec.model_dump()).insert()

    async def get(self, image_id: str) -> UploadRecord | None:
        return _rec(await self.col.find_one({"image_id": image_id}))

    async def acquire(self, image_id: str, owner: str, now: datetime) -> UploadRecord | None:
        d = await self.col.find_one_and_update(
            {"image_id": image_id, "owner_session_hash": owner, "expired": False, "expires_at": {"$gt": now}},
            {"$inc": {"reference_count": 1}},
            return_document=ReturnDocument.AFTER,
        )
        return _rec(d)

    async def release(self, image_id: str) -> UploadRecord | None:
        d = await self.col.find_one_and_update(
            {"image_id": image_id}, {"$inc": {"reference_count": -1}}, return_document=ReturnDocument.AFTER
        )
        return _rec(d)

    async def delete_unreferenced(self, image_id: str) -> bool:
        r = await self.col.delete_one({"image_id": image_id, "reference_count": {"$lte": 0}})
        return r.deleted_count == 1

    async def mark_expired(self, image_id: str, now: datetime) -> bool:
        r = await self.col.update_one({"image_id": image_id, "expired": False},
                                      {"$set": {"expired": True, "expired_at": now}})
        return r.modified_count == 1

    async def due_for_expiry(self, now: datetime) -> list[UploadRecord]:
        cur = self.col.find({"expired": False, "expires_at": {"$lte": now}})
        return [_rec(d) async for d in cur]

    async def unreferenced_expired(self) -> list[UploadRecord]:
        cur = self.col.find({"expired": True, "reference_count": {"$lte": 0}})
        return [_rec(d) async for d in cur]

    async def storage_keys(self) -> set[str]:
        cur = self.col.find({}, {"storage_key": 1})
        return {d["storage_key"] async for d in cur}
