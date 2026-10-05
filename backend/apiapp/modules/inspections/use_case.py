"""Inspection service (Spec §11.1-§11.2): validate, enqueue (202), read, list, delete."""

import base64
import json
import math
from datetime import datetime, timedelta

import numpy as np
from ai.preprocessing.geometry import validate_reference_points  # numpy + cv2 only, no paddle
from fastapi import Request
from loguru import logger

from ...core.config import Settings
from ...core.errors import AppError, ErrorCode
from ...core.ids import is_valid_id, new_id, utcnow
from ...core.session import same_owner
from ..layouts.use_case import LayoutService
from ..uploads.use_case import UploadService
from .model import ACTIVE_STATUSES, InspectionRecord
from .repository import Cursor, InspectionRepo
from .schemas import Inspection, InspectionAccepted, InspectionCreate, InspectionList, InspectionListItem


def normalized_to_px(points: list[list[float]], width: int, height: int) -> np.ndarray:
    return np.array([[x * width, y * height] for x, y in points], dtype=float)


def check_reference_points(points: list[list[float]], width: int, height: int) -> None:
    """4 finite points in [0,1], convex, non-crossing, large enough (same rule as the Inspector)."""
    if len(points) != 4 or any(len(p) != 2 for p in points):
        raise AppError(ErrorCode.INVALID_CORNERS)
    if any(not math.isfinite(v) or v < 0 or v > 1 for p in points for v in p):
        raise AppError(ErrorCode.INVALID_CORNERS)
    if validate_reference_points(normalized_to_px(points, width, height), (width, height)) is not None:
        raise AppError(ErrorCode.INVALID_CORNERS)


def encode_cursor(rec: InspectionRecord) -> str:
    raw = json.dumps([rec.created_at.isoformat(), rec.inspection_id]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> Cursor:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        ts, iid = json.loads(raw)
        created = datetime.fromisoformat(ts)
        if created.tzinfo is None or not is_valid_id(iid, "ins"):
            raise ValueError
        return created, iid
    except Exception as e:
        raise AppError(ErrorCode.VALIDATION_ERROR, "cursor ไม่ถูกต้อง") from e


class InspectionService:
    def __init__(self, settings: Settings, inspections: InspectionRepo, upload_service: UploadService,
                 layout_service: LayoutService) -> None:
        self.settings = settings
        self.inspections = inspections
        self.uploads = upload_service
        self.layouts = layout_service

    def status_url(self, inspection_id: str) -> str:
        return f"{self.settings.api_v1}/inspections/{inspection_id}"

    def _accepted(self, rec: InspectionRecord) -> InspectionAccepted:
        return InspectionAccepted(inspection_id=rec.inspection_id, status=rec.status,
                                  status_url=self.status_url(rec.inspection_id))

    async def create(self, owner: str, body: InspectionCreate) -> InspectionAccepted:
        crid = body.client_request_id
        if crid and (old := await self.inspections.find_by_client_request(owner, crid)):
            return self._accepted(old)
        layout = await self.layouts.get_public(body.layout_id)
        if layout is None:
            raise AppError(ErrorCode.LAYOUT_NOT_FOUND)
        upload = await self.uploads.get_owned(owner, body.image_id)
        if UploadService.is_expired(upload):
            raise AppError(ErrorCode.IMAGE_EXPIRED)
        check_reference_points(body.reference_points_normalized, upload.width, upload.height)

        await self.uploads.acquire_reference(owner, body.image_id)
        now = utcnow()
        rec = InspectionRecord(
            inspection_id=new_id("ins"), owner_session_hash=owner, client_request_id=crid,
            image_id=upload.image_id, image_width=upload.width, image_height=upload.height,
            layout_id=layout.layout_id, layout_version=layout.version,
            reference_points_normalized=[[float(x), float(y)] for x, y in body.reference_points_normalized],
            created_at=now, expires_at=now + timedelta(hours=self.settings.METADATA_RETENTION_HOURS),
        )
        try:
            saved, created = await self.inspections.create(
                rec, queue_capacity=self.settings.QUEUE_CAPACITY,
                max_per_owner=self.settings.MAX_ACTIVE_JOBS_PER_SESSION)
        except BaseException:
            await self.uploads.release_reference(body.image_id)
            raise
        if not created:
            await self.uploads.release_reference(body.image_id)
        else:
            logger.info("inspection queued inspection_id={} image_id={}", saved.inspection_id, saved.image_id)
        return self._accepted(saved)

    async def get_owned(self, owner: str, inspection_id: str) -> InspectionRecord:
        rec = await self.inspections.get(inspection_id) if is_valid_id(inspection_id, "ins") else None
        if rec is None or not same_owner(rec.owner_session_hash, owner):
            raise AppError(ErrorCode.NOT_FOUND)
        return rec

    async def _image_expired(self, image_id: str) -> bool:
        return UploadService.is_expired(await self.uploads.uploads.get(image_id))

    async def get(self, owner: str, inspection_id: str) -> Inspection:
        rec = await self.get_owned(owner, inspection_id)
        return self.to_inspection(rec, await self._image_expired(rec.image_id))

    def to_inspection(self, rec: InspectionRecord, image_expired: bool) -> Inspection:
        done = rec.status == "completed"
        return Inspection(
            inspection_id=rec.inspection_id, status=rec.status, stage=rec.stage if rec.status == "processing" else None,
            image_id=rec.image_id, image_url=self.uploads.image_url(rec.image_id),
            image_width=rec.image_width, image_height=rec.image_height, image_expired=image_expired,
            layout_id=rec.layout_id, layout_version=rec.layout_version, model_bundle_id=rec.model_bundle_id,
            reference_points_normalized=rec.reference_points_normalized,
            created_at=rec.created_at, finished_at=rec.finished_at,
            summary=rec.summary if done else None,
            slots=rec.slots if done else [],
            suggestions=rec.suggestions if done else [],
            warnings=rec.warnings, timings_ms=rec.timings_ms, error=rec.error,
        )

    async def list(self, owner: str, limit: int, cursor: str | None) -> InspectionList:
        after = decode_cursor(cursor) if cursor else None
        recs = await self.inspections.list_for_owner(owner, limit + 1, after)
        page, more = recs[:limit], len(recs) > limit
        items = [
            InspectionListItem(
                inspection_id=r.inspection_id, status=r.status, stage=r.stage if r.status == "processing" else None,
                image_id=r.image_id, image_url=self.uploads.image_url(r.image_id),
                image_expired=await self._image_expired(r.image_id), layout_id=r.layout_id,
                model_bundle_id=r.model_bundle_id, created_at=r.created_at, finished_at=r.finished_at,
                summary=r.summary if r.status == "completed" else None, error=r.error,
            )
            for r in page
        ]
        return InspectionList(items=items, next_cursor=encode_cursor(page[-1]) if more and page else None)

    async def delete(self, owner: str, inspection_id: str) -> None:
        rec = await self.get_owned(owner, inspection_id)
        if rec.status in ACTIVE_STATUSES:
            raise AppError(ErrorCode.INSPECTION_IN_PROGRESS)
        deleted = await self.inspections.delete_terminal(inspection_id)
        if deleted is None:
            raise AppError(ErrorCode.NOT_FOUND)
        await self.uploads.release_reference(deleted.image_id)
        logger.info("inspection deleted inspection_id={}", inspection_id)


def get_inspection_service(request: Request) -> InspectionService:
    return request.app.state.container.inspection_service
