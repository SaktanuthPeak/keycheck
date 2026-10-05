from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class UploadResponse(BaseModel):
    image_id: str
    width: int
    height: int
    mime_type: Literal["image/jpeg", "image/png"]
    byte_size: int
    image_url: str
    created_at: datetime
    expires_at: datetime
