"""inspections (Spec §12.3): one document per job; it is also the queue entry (status=queued, claimed atomically)."""

from datetime import datetime
from typing import Any, Literal

from beanie import Document
from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING, IndexModel

Status = Literal["queued", "processing", "completed", "rejected", "failed"]
ACTIVE_STATUSES: tuple[str, ...] = ("queued", "processing")
TERMINAL_STATUSES: tuple[str, ...] = ("completed", "rejected", "failed")


class WorkerLease(BaseModel):
    worker_id: str | None = None
    claimed_at: datetime | None = None
    heartbeat_at: datetime | None = None
    retry_count: int = 0


class InspectionRecord(BaseModel):
    inspection_id: str
    owner_session_hash: str
    client_request_id: str | None = None
    image_id: str
    image_width: int  # oriented size of the stored image, used to map normalised points
    image_height: int
    layout_id: str
    layout_version: int
    reference_points_normalized: list[list[float]]
    homography: list[list[float]] | None = None
    model_bundle_id: str | None = None
    status: Status = "queued"
    stage: str | None = None
    summary: dict[str, Any] | None = None
    slots: list[dict[str, Any]] = Field(default_factory=list)
    suggestions: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: dict[str, Any] | None = None
    timings_ms: dict[str, Any] | None = None
    fit: dict[str, Any] | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    expires_at: datetime
    worker_lease: WorkerLease = Field(default_factory=WorkerLease)


class InspectionDoc(Document, InspectionRecord):
    class Settings:
        name = "inspections"
        indexes = [
            IndexModel([("inspection_id", ASCENDING)], unique=True, name="inspection_id_unique"),
            IndexModel([("owner_session_hash", ASCENDING), ("created_at", DESCENDING)], name="owner_created"),
            IndexModel([("status", ASCENDING), ("created_at", ASCENDING)], name="status_created"),
            IndexModel([("image_id", ASCENDING)], name="image"),
            IndexModel(
                [("owner_session_hash", ASCENDING), ("client_request_id", ASCENDING)],
                unique=True,
                partialFilterExpression={"client_request_id": {"$type": "string"}},
                name="owner_client_request_unique",
            ),
        ]
