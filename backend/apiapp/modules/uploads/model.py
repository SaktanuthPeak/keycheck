"""uploads (Spec §12.2): metadata only; the image file lives in ImageStorage under `storage_key`."""

from datetime import datetime

from beanie import Document
from pydantic import BaseModel
from pymongo import ASCENDING, DESCENDING, IndexModel


class UploadRecord(BaseModel):
    image_id: str
    owner_session_hash: str
    storage_key: str
    mime_type: str
    byte_size: int
    width: int  # oriented (after EXIF transpose)
    height: int
    sha256: str  # of the bytes the client sent
    created_at: datetime
    expires_at: datetime
    reference_count: int = 0  # inspections that point at this image
    expired: bool = False  # file deleted by retention; metadata kept while referenced
    expired_at: datetime | None = None


class UploadDoc(Document, UploadRecord):
    class Settings:
        name = "uploads"
        indexes = [
            IndexModel([("image_id", ASCENDING)], unique=True, name="image_id_unique"),
            IndexModel([("owner_session_hash", ASCENDING), ("created_at", DESCENDING)], name="owner_created"),
            IndexModel([("expired", ASCENDING), ("expires_at", ASCENDING)], name="expiry"),
        ]
