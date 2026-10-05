"""Retention worker (Spec §12.5): delete image files after IMAGE_RETENTION_HOURS (metadata says image_expired),
inspection metadata after METADATA_RETENTION_HOURS, unreferenced upload records, and orphan files."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from loguru import logger

from ..core.ids import utcnow


@dataclass
class RetentionReport:
    inspections_deleted: int = 0
    images_expired: int = 0
    uploads_deleted: int = 0
    orphans_deleted: int = 0


class RetentionService:
    def __init__(self, container) -> None:
        self.c = container

    async def run_once(self, now: datetime | None = None) -> RetentionReport:
        c, s = self.c, self.c.settings
        now = now or utcnow()
        rep = RetentionReport()

        # 1. inspection metadata (finished jobs only; queued/processing are never removed under the worker)
        for rec in await c.inspections.terminal_created_before(now - timedelta(hours=s.METADATA_RETENTION_HOURS)):
            if await c.inspections.delete_terminal(rec.inspection_id) is not None:
                await c.upload_service.release_reference(rec.image_id)
                rep.inspections_deleted += 1

        # 2. image files past expires_at, unless a job still needs them
        for up in await c.uploads.due_for_expiry(now):
            if await c.inspections.count_active_for_image(up.image_id):
                continue
            if await c.uploads.mark_expired(up.image_id, now):
                c.storage.delete(up.storage_key)
                rep.images_expired += 1

        # 3. expired upload records nobody references any more
        for up in await c.uploads.unreferenced_expired():
            if await c.uploads.delete_unreferenced(up.image_id):
                c.storage.delete(up.storage_key)
                rep.uploads_deleted += 1

        # 4. files without a live upload record (crash between write and insert, manual copies, temp files).
        # List files before reading the keys; the grace period covers uploads between file write and insert.
        candidates = c.storage.keys_older_than(s.ORPHAN_GRACE_SECONDS)
        known = await c.uploads.storage_keys()
        for name in candidates:
            if name not in known:
                c.storage.remove_stale(name)
                rep.orphans_deleted += 1

        if any(vars(rep).values()):
            logger.info("retention: {}", vars(rep))
        return rep
