"""Inference worker (Spec §4.3, implementation plan P5.A-9).

One loop per worker: load the Inspector once, then claim the oldest queued job, keep its lease alive with
heartbeats while inference runs in a thread, store the result. Expired leases (crashed workers) are requeued up
to WORKER_MAX_RETRIES and then failed. Retention runs on the same loop. Used by `python -m apiapp.worker`
(MongoDB mode) and by the worker thread inside the API process (memory mode).
"""

import asyncio
import os
import secrets
import socket
import threading
import time
from typing import Any

import numpy as np
from loguru import logger
from pydantic import ValidationError

from ..core.errors import ErrorCode, error_body
from ..core.ids import utcnow
from ..modules.inspections.model import InspectionRecord
from ..modules.inspections.schemas import Slot, Suggestion, Summary
from ..modules.inspections.use_case import normalized_to_px
from ..modules.model_bundles.model import ModelBundleRecord, WorkerStatus
from .inspector import InspectorFactory, is_invalid_reference_points, read_bundle_meta
from .retention import RetentionService

REJECT_CODES = (ErrorCode.LAYOUT_MISMATCH, ErrorCode.INVALID_CORNERS)


def _read_bgr(path) -> np.ndarray | None:
    import cv2

    return cv2.imread(str(path), cv2.IMREAD_COLOR)


def terminal_fields(status: str, code: ErrorCode | None = None, **extra: Any) -> dict[str, Any]:
    fields = {"status": status, "stage": None, "finished_at": utcnow(), "error": error_body(code) if code else None,
              "summary": None, "slots": [], "suggestions": []}
    fields.update(extra)
    return fields


class InspectionWorker:
    def __init__(self, container, inspector_factory: InspectorFactory, *, worker_id: str | None = None) -> None:
        self.c = container
        self.s = container.settings
        self.factory = inspector_factory
        self.worker_id = worker_id or f"{socket.gethostname()}-{os.getpid()}-{secrets.token_hex(3)}"
        self.inspectors: dict[str, Any] = {}
        self.model_status = "loading"
        self.model_error: str | None = None
        meta = read_bundle_meta(self.s.MODEL_BUNDLE_DIR) or {}
        self.bundle_id: str | None = meta.get("bundle_id")
        self.started_at = utcnow()
        self.retention = RetentionService(container)

    # ---- lifecycle -------------------------------------------------------------------------------------------
    async def run(self, stop: threading.Event) -> None:
        logger.info("worker {} starting", self.worker_id)
        await self._safe(self.publish_status())
        status_task = asyncio.create_task(self._status_loop())
        try:
            await self._load(self.s.DEFAULT_LAYOUT_ID)
            await self._safe(self._register_bundle())
            last_recover = last_retention = float("-inf")
            while not stop.is_set():
                t = time.monotonic()
                if t - last_recover >= self.s.heartbeat_seconds:
                    last_recover = t
                    await self._safe(self.recover_leases())
                if t - last_retention >= self.s.RETENTION_INTERVAL_SECONDS:
                    last_retention = t
                    await self._safe(self.retention.run_once())
                try:
                    job = await self.c.inspections.claim(self.worker_id, utcnow(), self.s.WORKER_POLL_SECONDS)
                except Exception as e:
                    logger.error("claim failed: {}", type(e).__name__)
                    await asyncio.sleep(self.s.WORKER_POLL_SECONDS)
                    continue
                if job is not None:
                    await self.process(job)
        finally:
            status_task.cancel()
            logger.info("worker {} stopped", self.worker_id)

    async def _safe(self, coro) -> Any:
        try:
            return await coro
        except Exception as e:
            logger.opt(exception=e).error("worker maintenance step failed: {}", type(e).__name__)
            return None

    async def publish_status(self) -> None:
        await self.c.worker_status.put(WorkerStatus(
            worker_id=self.worker_id, model_status=self.model_status, model_bundle_id=self.bundle_id,
            error_code=self.model_error, started_at=self.started_at, heartbeat_at=utcnow()))

    async def _status_loop(self) -> None:
        while True:
            await asyncio.sleep(self.s.heartbeat_seconds)
            await self._safe(self.publish_status())

    async def _load(self, layout_id: str) -> Any:
        try:
            insp = await asyncio.to_thread(self.factory, layout_id)
        except Exception as e:
            logger.error("model load failed for layout {}: {}: {}", layout_id, type(e).__name__, e)
            self.inspectors[layout_id] = None
            self.model_status, self.model_error = "error", ErrorCode.MODEL_UNAVAILABLE.value
        else:
            self.inspectors[layout_id] = insp
            self.bundle_id = getattr(insp, "bundle_id", None) or self.bundle_id
            self.model_status, self.model_error = "ready", None
            logger.info("model ready bundle={} layout={}", self.bundle_id, layout_id)
        await self._safe(self.publish_status())
        return self.inspectors[layout_id]

    async def _inspector_for(self, layout_id: str) -> Any:
        if layout_id in self.inspectors:
            return self.inspectors[layout_id]
        return await self._load(layout_id)

    async def _register_bundle(self) -> None:
        meta = read_bundle_meta(self.s.MODEL_BUNDLE_DIR)
        if not meta or not (meta.get("bundle_id") or self.bundle_id):
            return
        await self.c.model_bundles.register_active(ModelBundleRecord(
            bundle_id=meta.get("bundle_id") or self.bundle_id,
            detector_architecture=meta.get("detector"),
            checkpoint_hash=meta.get("bundle_sha256"),
            ocr_model_id=meta.get("ocr"),
            preprocessing_version=f"px{meta.get('px_per_unit')}_{meta.get('crop_mode')}",
            thresholds=meta.get("thresholds"),
            dataset_version=meta.get("dataset_version") or meta.get("proxy"),
            split_manifest_hash=meta.get("split_manifest_hash"),
            library_versions=meta.get("library_versions"),
            validation_metrics=meta.get("validation_metrics"),
            registered_at=utcnow(),
        ))

    async def recover_leases(self) -> None:
        requeued, failed = await self.c.inspections.recover_expired_leases(
            utcnow(), self.s.WORKER_LEASE_SECONDS, self.s.WORKER_MAX_RETRIES,
            terminal_fields("failed", ErrorCode.PROCESSING_FAILED))
        for iid in requeued:
            logger.warning("lease expired, requeued inspection_id={}", iid)
        for iid in failed:
            logger.warning("lease expired, retries exhausted inspection_id={} -> failed", iid)

    # ---- one job ---------------------------------------------------------------------------------------------
    async def process(self, job: InspectionRecord) -> None:
        t0 = time.monotonic()
        lease = asyncio.create_task(self._lease_loop(job.inspection_id))
        try:
            fields = await self._execute(job)
        except Exception as e:
            logger.opt(exception=e).error("worker error inspection_id={}: {}", job.inspection_id, type(e).__name__)
            fields = terminal_fields("failed", ErrorCode.PROCESSING_FAILED)
        finally:
            lease.cancel()
        ok = await self.c.inspections.finish(job.inspection_id, self.worker_id, fields)
        code = (fields.get("error") or {}).get("code")
        if ok:
            logger.info("inspection_id={} -> {} code={} ({:.0f} ms)", job.inspection_id, fields["status"], code,
                        (time.monotonic() - t0) * 1000)
        else:
            logger.warning("inspection_id={} result dropped: lease lost", job.inspection_id)

    async def _lease_loop(self, inspection_id: str) -> None:
        while True:
            await asyncio.sleep(self.s.heartbeat_seconds)
            try:
                if not await self.c.inspections.heartbeat(inspection_id, self.worker_id, utcnow()):
                    logger.warning("heartbeat rejected inspection_id={}", inspection_id)
                    return
            except Exception as e:
                logger.error("heartbeat failed inspection_id={}: {}", inspection_id, type(e).__name__)

    async def _execute(self, job: InspectionRecord) -> dict[str, Any]:
        upload = await self.c.uploads.get(job.image_id)
        if upload is None or upload.expired or not self.c.storage.exists(upload.storage_key):
            return terminal_fields("failed", ErrorCode.IMAGE_EXPIRED)
        insp = await self._inspector_for(job.layout_id)
        if insp is None:
            return terminal_fields("failed", ErrorCode.MODEL_UNAVAILABLE, model_bundle_id=self.bundle_id)
        img = await asyncio.to_thread(_read_bgr, self.c.storage.path(upload.storage_key))
        if img is None:
            return terminal_fields("failed", ErrorCode.PROCESSING_FAILED)
        if img.shape[1] != job.image_width or img.shape[0] != job.image_height:
            logger.warning("inspection_id={} stored size differs from decoded size", job.inspection_id)
        pts = normalized_to_px(job.reference_points_normalized, job.image_width, job.image_height)

        loop = asyncio.get_running_loop()
        iid, wid = job.inspection_id, self.worker_id

        def on_stage(stage: str) -> None:  # called from the inference thread
            asyncio.run_coroutine_threadsafe(self.c.inspections.set_stage(iid, wid, stage), loop)

        bundle_id = getattr(insp, "bundle_id", None) or self.bundle_id
        try:
            result = await asyncio.to_thread(insp.inspect, img, pts, on_stage=on_stage)
        except Exception as e:
            if is_invalid_reference_points(e):
                return terminal_fields("rejected", ErrorCode.INVALID_CORNERS, model_bundle_id=bundle_id)
            logger.opt(exception=e).error("inspect failed inspection_id={}: {}", iid, type(e).__name__)
            return terminal_fields("failed", ErrorCode.PROCESSING_FAILED, model_bundle_id=bundle_id)
        return self._from_result(job, result, bundle_id)

    def _from_result(self, job: InspectionRecord, result: dict, bundle_id: str | None) -> dict[str, Any]:
        common: dict[str, Any] = {
            "model_bundle_id": result.get("model_bundle_id") or bundle_id,
            "layout_version": int(result.get("layout_version") or job.layout_version),
            "warnings": [str(w) for w in result.get("warnings") or []],
            "timings_ms": result.get("timings_ms"),
            "fit": result.get("fit"),
        }
        if result.get("homography") is not None:
            try:
                common["homography"] = np.asarray(result["homography"], float).reshape(3, 3).tolist()
            except (TypeError, ValueError):
                pass
        status = result.get("status")
        if status == "completed":
            try:
                summary = Summary.model_validate(result["summary"])
                slots = [Slot.model_validate(s) for s in result["slots"]]
                suggestions = [Suggestion.model_validate(s) for s in result.get("suggestions") or []]
            except (KeyError, TypeError, ValidationError) as e:
                logger.error("inspection_id={} result violates the contract: {}", job.inspection_id,
                             type(e).__name__)
                return terminal_fields("failed", ErrorCode.PROCESSING_FAILED, **common)
            if not (summary.correct + summary.incorrect + summary.uncertain == summary.total_slots == len(slots)):
                logger.error("inspection_id={} summary does not add up", job.inspection_id)
                return terminal_fields("failed", ErrorCode.PROCESSING_FAILED, **common)
            return terminal_fields(
                "completed", None, summary=summary.model_dump(), slots=[s.model_dump() for s in slots],
                suggestions=[s.model_dump() for s in suggestions], **common)
        if status == "rejected":
            code = result.get("error_code")
            code = ErrorCode(code) if code in REJECT_CODES else ErrorCode.LAYOUT_MISMATCH
            return terminal_fields("rejected", code, **common)
        logger.error("inspection_id={} unexpected inspector status", job.inspection_id)
        return terminal_fields("failed", ErrorCode.PROCESSING_FAILED, **common)
