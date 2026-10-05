"""InspectionRepo = job store + queue.

- Memory (W2): dict + threading.Lock, queue.Queue of ids; the worker thread lives in the API process.
- MongoDB (W6): the `inspections` collection is the queue; claim = find_one_and_update on the oldest
  `queued` job; guarded writes use (status=processing, worker_lease.worker_id), so a requeued job
  cannot be overwritten by a stale worker.
"""

import asyncio
import queue
import threading
from datetime import datetime, timedelta
from typing import Any, Protocol

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from ...core.errors import AppError, ErrorCode
from .model import ACTIVE_STATUSES, TERMINAL_STATUSES, InspectionDoc, InspectionRecord, WorkerLease

Cursor = tuple[datetime, str]  # (created_at, inspection_id) of the last item of the previous page


class InspectionRepo(Protocol):
    async def create(self, rec: InspectionRecord, *, queue_capacity: int,
                     max_per_owner: int) -> tuple[InspectionRecord, bool]:
        """Insert as queued. Same (owner, client_request_id) -> (existing, False). Over capacity -> QUEUE_FULL."""
        ...

    async def get(self, inspection_id: str) -> InspectionRecord | None: ...

    async def find_by_client_request(self, owner: str, client_request_id: str) -> InspectionRecord | None: ...

    async def list_for_owner(self, owner: str, limit: int, after: Cursor | None) -> list[InspectionRecord]: ...

    async def delete_terminal(self, inspection_id: str) -> InspectionRecord | None:
        """Delete only if completed/rejected/failed; returns the deleted record."""
        ...

    async def claim(self, worker_id: str, now: datetime, wait: float) -> InspectionRecord | None:
        """Oldest queued job -> processing with a fresh lease. May block up to `wait` seconds when idle."""
        ...

    async def set_stage(self, inspection_id: str, worker_id: str, stage: str) -> bool: ...

    async def heartbeat(self, inspection_id: str, worker_id: str, now: datetime) -> bool: ...

    async def finish(self, inspection_id: str, worker_id: str, fields: dict[str, Any]) -> bool: ...

    async def recover_expired_leases(self, now: datetime, lease_seconds: float, max_retries: int,
                                     failed_fields: dict[str, Any]) -> tuple[list[str], list[str]]:
        """processing jobs whose heartbeat is older than the lease: requeue (retry_count+1) while
        retry_count < max_retries, else set `failed_fields`. Returns (requeued_ids, failed_ids)."""
        ...

    async def count_active_for_image(self, image_id: str) -> int: ...

    async def terminal_created_before(self, before: datetime) -> list[InspectionRecord]: ...


def _after(rec: InspectionRecord, after: Cursor | None) -> bool:
    if after is None:
        return True
    c, iid = after
    return rec.created_at < c or (rec.created_at == c and rec.inspection_id < iid)


class MemoryInspectionRepo:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, InspectionRecord] = {}
        self._queue: queue.Queue[str] = queue.Queue()

    @staticmethod
    def _copy(rec: InspectionRecord | None) -> InspectionRecord | None:
        return rec.model_copy(deep=True) if rec is not None else None

    def _find_crid(self, owner: str, crid: str) -> InspectionRecord | None:
        for r in self._items.values():
            if r.client_request_id == crid and r.owner_session_hash == owner:
                return r
        return None

    async def create(self, rec: InspectionRecord, *, queue_capacity: int,
                     max_per_owner: int) -> tuple[InspectionRecord, bool]:
        with self._lock:
            if rec.client_request_id and (old := self._find_crid(rec.owner_session_hash, rec.client_request_id)):
                return self._copy(old), False
            active = [r for r in self._items.values() if r.status in ACTIVE_STATUSES]
            if len(active) >= queue_capacity:
                raise AppError(ErrorCode.QUEUE_FULL)
            if sum(r.owner_session_hash == rec.owner_session_hash for r in active) >= max_per_owner:
                raise AppError(ErrorCode.QUEUE_FULL)
            self._items[rec.inspection_id] = rec.model_copy(deep=True)
            self._queue.put(rec.inspection_id)
            return self._copy(rec), True

    async def get(self, inspection_id: str) -> InspectionRecord | None:
        with self._lock:
            return self._copy(self._items.get(inspection_id))

    async def find_by_client_request(self, owner: str, client_request_id: str) -> InspectionRecord | None:
        with self._lock:
            return self._copy(self._find_crid(owner, client_request_id))

    async def list_for_owner(self, owner: str, limit: int, after: Cursor | None) -> list[InspectionRecord]:
        with self._lock:
            mine = [r for r in self._items.values() if r.owner_session_hash == owner and _after(r, after)]
            mine.sort(key=lambda r: (r.created_at, r.inspection_id), reverse=True)
            return [r.model_copy(deep=True) for r in mine[:limit]]

    async def delete_terminal(self, inspection_id: str) -> InspectionRecord | None:
        with self._lock:
            rec = self._items.get(inspection_id)
            if rec is None or rec.status not in TERMINAL_STATUSES:
                return None
            return self._items.pop(inspection_id)

    async def claim(self, worker_id: str, now: datetime, wait: float) -> InspectionRecord | None:
        try:
            iid = await asyncio.to_thread(self._queue.get, True, wait)
        except queue.Empty:
            return None
        with self._lock:
            rec = self._items.get(iid)
            if rec is None or rec.status != "queued":
                return None
            rec.status, rec.stage, rec.started_at = "processing", None, now
            rec.worker_lease = WorkerLease(worker_id=worker_id, claimed_at=now, heartbeat_at=now,
                                           retry_count=rec.worker_lease.retry_count)
            return self._copy(rec)

    def _owned(self, inspection_id: str, worker_id: str) -> InspectionRecord | None:
        rec = self._items.get(inspection_id)
        if rec is None or rec.status != "processing" or rec.worker_lease.worker_id != worker_id:
            return None
        return rec

    async def set_stage(self, inspection_id: str, worker_id: str, stage: str) -> bool:
        with self._lock:
            if (rec := self._owned(inspection_id, worker_id)) is None:
                return False
            rec.stage = stage
            return True

    async def heartbeat(self, inspection_id: str, worker_id: str, now: datetime) -> bool:
        with self._lock:
            if (rec := self._owned(inspection_id, worker_id)) is None:
                return False
            rec.worker_lease.heartbeat_at = now
            return True

    async def finish(self, inspection_id: str, worker_id: str, fields: dict[str, Any]) -> bool:
        with self._lock:
            if (rec := self._owned(inspection_id, worker_id)) is None:
                return False
            self._items[inspection_id] = rec.model_copy(update=fields, deep=True)
            return True

    async def recover_expired_leases(self, now: datetime, lease_seconds: float, max_retries: int,
                                     failed_fields: dict[str, Any]) -> tuple[list[str], list[str]]:
        cutoff = now - timedelta(seconds=lease_seconds)
        requeued, failed = [], []
        with self._lock:
            for iid, rec in list(self._items.items()):
                hb = rec.worker_lease.heartbeat_at
                if rec.status != "processing" or hb is None or hb >= cutoff:
                    continue
                if rec.worker_lease.retry_count < max_retries:
                    rec.status, rec.stage, rec.started_at = "queued", None, None
                    rec.worker_lease = WorkerLease(retry_count=rec.worker_lease.retry_count + 1)
                    self._queue.put(iid)
                    requeued.append(iid)
                else:
                    self._items[iid] = rec.model_copy(update=failed_fields, deep=True)
                    failed.append(iid)
        return requeued, failed

    async def count_active_for_image(self, image_id: str) -> int:
        with self._lock:
            return sum(r.image_id == image_id and r.status in ACTIVE_STATUSES for r in self._items.values())

    async def terminal_created_before(self, before: datetime) -> list[InspectionRecord]:
        with self._lock:
            return [r.model_copy(deep=True) for r in self._items.values()
                    if r.status in TERMINAL_STATUSES and r.created_at <= before]


def _rec(d: dict | None) -> InspectionRecord | None:
    if d is None:
        return None
    d.pop("_id", None)
    d.pop("revision_id", None)
    return InspectionRecord.model_validate(d)


class MongoInspectionRepo:
    @property
    def col(self):
        return InspectionDoc.get_pymongo_collection()

    async def create(self, rec: InspectionRecord, *, queue_capacity: int,
                     max_per_owner: int) -> tuple[InspectionRecord, bool]:
        owner, crid = rec.owner_session_hash, rec.client_request_id
        if crid and (old := await self.find_by_client_request(owner, crid)):
            return old, False
        # Soft limits: count-then-insert is not atomic across API processes; one API process is the MVP setup.
        active = {"status": {"$in": list(ACTIVE_STATUSES)}}
        if await self.col.count_documents(active) >= queue_capacity:
            raise AppError(ErrorCode.QUEUE_FULL)
        if await self.col.count_documents({**active, "owner_session_hash": owner}) >= max_per_owner:
            raise AppError(ErrorCode.QUEUE_FULL)
        try:
            await self.col.insert_one(rec.model_dump())
        except DuplicateKeyError:
            if crid and (old := await self.find_by_client_request(owner, crid)):
                return old, False
            raise
        return rec, True

    async def get(self, inspection_id: str) -> InspectionRecord | None:
        return _rec(await self.col.find_one({"inspection_id": inspection_id}))

    async def find_by_client_request(self, owner: str, client_request_id: str) -> InspectionRecord | None:
        return _rec(await self.col.find_one({"owner_session_hash": owner, "client_request_id": client_request_id}))

    async def list_for_owner(self, owner: str, limit: int, after: Cursor | None) -> list[InspectionRecord]:
        q: dict[str, Any] = {"owner_session_hash": owner}
        if after is not None:
            c, iid = after
            q["$or"] = [{"created_at": {"$lt": c}}, {"created_at": c, "inspection_id": {"$lt": iid}}]
        cur = self.col.find(q, {"slots": 0, "fit": 0}).sort([("created_at", -1), ("inspection_id", -1)]).limit(limit)
        return [_rec(d) async for d in cur]

    async def delete_terminal(self, inspection_id: str) -> InspectionRecord | None:
        d = await self.col.find_one_and_delete(
            {"inspection_id": inspection_id, "status": {"$in": list(TERMINAL_STATUSES)}}
        )
        return _rec(d)

    async def claim(self, worker_id: str, now: datetime, wait: float) -> InspectionRecord | None:
        d = await self.col.find_one_and_update(
            {"status": "queued"},
            {"$set": {"status": "processing", "stage": None, "started_at": now,
                      "worker_lease.worker_id": worker_id, "worker_lease.claimed_at": now,
                      "worker_lease.heartbeat_at": now}},
            sort=[("created_at", 1)],
            return_document=ReturnDocument.AFTER,
        )
        if d is None:
            await asyncio.sleep(wait)
        return _rec(d)

    @staticmethod
    def _owned(inspection_id: str, worker_id: str) -> dict:
        return {"inspection_id": inspection_id, "status": "processing", "worker_lease.worker_id": worker_id}

    async def set_stage(self, inspection_id: str, worker_id: str, stage: str) -> bool:
        r = await self.col.update_one(self._owned(inspection_id, worker_id), {"$set": {"stage": stage}})
        return r.matched_count == 1

    async def heartbeat(self, inspection_id: str, worker_id: str, now: datetime) -> bool:
        r = await self.col.update_one(self._owned(inspection_id, worker_id),
                                      {"$set": {"worker_lease.heartbeat_at": now}})
        return r.matched_count == 1

    async def finish(self, inspection_id: str, worker_id: str, fields: dict[str, Any]) -> bool:
        r = await self.col.update_one(self._owned(inspection_id, worker_id), {"$set": fields})
        return r.matched_count == 1

    async def recover_expired_leases(self, now: datetime, lease_seconds: float, max_retries: int,
                                     failed_fields: dict[str, Any]) -> tuple[list[str], list[str]]:
        cutoff = now - timedelta(seconds=lease_seconds)
        stale = {"status": "processing", "worker_lease.heartbeat_at": {"$lt": cutoff}}
        requeued, failed = [], []
        async for d in self.col.find(stale, {"inspection_id": 1, "worker_lease": 1}):
            iid = d["inspection_id"]
            rc = int((d.get("worker_lease") or {}).get("retry_count") or 0)
            guard = {**stale, "inspection_id": iid}
            if rc < max_retries:
                lease = WorkerLease(retry_count=rc + 1).model_dump()
                r = await self.col.update_one(guard, {"$set": {"status": "queued", "stage": None, "started_at": None,
                                                               "worker_lease": lease}})
                if r.modified_count:
                    requeued.append(iid)
            else:
                r = await self.col.update_one(guard, {"$set": failed_fields})
                if r.modified_count:
                    failed.append(iid)
        return requeued, failed

    async def count_active_for_image(self, image_id: str) -> int:
        return await self.col.count_documents({"image_id": image_id, "status": {"$in": list(ACTIVE_STATUSES)}})

    async def terminal_created_before(self, before: datetime) -> list[InspectionRecord]:
        cur = self.col.find({"status": {"$in": list(TERMINAL_STATUSES)}, "created_at": {"$lte": before}},
                            {"slots": 0, "fit": 0})
        return [_rec(d) async for d in cur]
