from typing import Literal

from pydantic import BaseModel


class ReferencePoint(BaseModel):
    order: Literal["TL", "TR", "BR", "BL"]
    slot_id: str
    expected_label: str


class LayoutSlot(BaseModel):
    slot_id: str
    row: int
    col: int
    expected_label: str


class LayoutResponse(BaseModel):
    layout_id: str
    version: int
    name: str
    supported_form_factors: list[str]
    reference_points: list[ReferencePoint]
    slots: list[LayoutSlot]


class LayoutListResponse(BaseModel):
    layouts: list[LayoutResponse]
