"""model_bundles (Spec §12.4) and worker_heartbeats (model readiness for /health in MongoDB mode)."""

from datetime import datetime
from typing import Any, Literal

from beanie import Document
from pydantic import BaseModel
from pymongo import ASCENDING, DESCENDING, IndexModel

ModelStatus = Literal["loading", "ready", "error"]


class ModelBundleRecord(BaseModel):
    bundle_id: str
    detector_architecture: str | None = None
    checkpoint_hash: str | None = None
    ocr_model_id: Any = None
    preprocessing_version: str | None = None
    thresholds: dict[str, Any] | None = None
    dataset_version: str | None = None
    split_manifest_hash: str | None = None
    library_versions: dict[str, Any] | None = None
    validation_metrics: dict[str, Any] | None = None
    active: bool = False
    registered_at: datetime


class ModelBundleDoc(Document, ModelBundleRecord):
    class Settings:
        name = "model_bundles"
        indexes = [IndexModel([("bundle_id", ASCENDING)], unique=True, name="bundle_id_unique")]


class WorkerStatus(BaseModel):
    worker_id: str
    model_status: ModelStatus
    model_bundle_id: str | None = None
    error_code: str | None = None
    started_at: datetime
    heartbeat_at: datetime


class WorkerHeartbeatDoc(Document, WorkerStatus):
    class Settings:
        name = "worker_heartbeats"
        indexes = [
            IndexModel([("worker_id", ASCENDING)], unique=True, name="worker_id_unique"),
            IndexModel([("heartbeat_at", DESCENDING)], name="heartbeat"),
        ]
