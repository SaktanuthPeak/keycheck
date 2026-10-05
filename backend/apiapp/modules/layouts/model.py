"""layouts (Spec §12.1): seeded from layouts/*.json; `definition` keeps the full versioned JSON."""

from beanie import Document
from pydantic import BaseModel
from pymongo import ASCENDING, DESCENDING, IndexModel


class LayoutRecord(BaseModel):
    layout_id: str
    version: int
    name: str
    supported_form_factors: list[str] = []
    internal_only: bool = False
    definition: dict


class LayoutDoc(Document, LayoutRecord):
    class Settings:
        name = "layouts"
        indexes = [
            IndexModel([("layout_id", ASCENDING), ("version", DESCENDING)], unique=True, name="layout_version_unique"),
        ]
