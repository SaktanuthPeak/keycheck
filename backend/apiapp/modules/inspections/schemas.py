"""Inspection API schemas (api-contract §2.1)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["queued", "processing", "completed", "rejected", "failed"]
Stage = Literal["rectifying", "detecting", "reading", "matching"]


class InspectionCreate(BaseModel):
    image_id: str = Field(max_length=64)
    layout_id: str = Field(max_length=128)
    reference_points_normalized: list[list[float]] = Field(
        description="4 points in 0..1 on the oriented image, order TL,TR,BR,BL = centres of slots Q,P,M,Z"
    )
    client_request_id: str | None = Field(default=None, min_length=1, max_length=128,
                                          description="Idempotency key, unique per session")


class InspectionAccepted(BaseModel):
    inspection_id: str
    status: Status
    status_url: str


class Summary(BaseModel):
    total_slots: int
    correct: int
    incorrect: int
    uncertain: int


class Slot(BaseModel):
    slot_id: str
    row: int
    col: int
    expected_label: str
    observed_label: str | None = None
    # uncertain + ocr_low_confidence: the letter read below the threshold (a hint, not a verdict)
    candidate_label: str | None = None
    status: Literal["correct", "incorrect", "uncertain"]
    reason: str
    reason_codes: list[str] = []
    detector_score: float | None = None
    ocr_score: float | None = None
    assignment_distance: float | None = None
    polygon: list[list[float]]
    polygon_source: Literal["detection", "layout"]
    is_reference: bool = False


class Suggestion(BaseModel):
    type: Literal["swap_pair", "cycle"]
    slots: list[str]


class ErrorInfo(BaseModel):
    code: str
    message: str
    retryable: bool


class Inspection(BaseModel):
    inspection_id: str
    status: Status
    stage: Stage | None = None
    image_id: str
    image_url: str
    image_width: int
    image_height: int
    image_expired: bool
    layout_id: str
    layout_version: int
    model_bundle_id: str | None = None
    coordinate_system: Literal["original_oriented_normalized"] = "original_oriented_normalized"
    reference_points_normalized: list[list[float]]
    created_at: datetime
    finished_at: datetime | None = None
    summary: Summary | None = None
    slots: list[Slot] = []
    suggestions: list[Suggestion] = []
    warnings: list[str] = []
    timings_ms: dict[str, float | int] | None = None
    error: ErrorInfo | None = None


class InspectionListItem(BaseModel):
    inspection_id: str
    status: Status
    stage: Stage | None = None
    image_id: str
    image_url: str
    image_expired: bool
    layout_id: str
    model_bundle_id: str | None = None
    created_at: datetime
    finished_at: datetime | None = None
    summary: Summary | None = None
    error: ErrorInfo | None = None


class InspectionList(BaseModel):
    items: list[InspectionListItem]
    next_cursor: str | None = None
