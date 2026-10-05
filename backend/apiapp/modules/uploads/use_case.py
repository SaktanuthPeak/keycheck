"""Upload service (Spec §11.1, api-contract §2): magic bytes, size/pixel limits, real decode, EXIF transpose,
metadata stripped by re-encoding, SHA-256, expiry."""

import hashlib
import io
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from fastapi import Request, UploadFile
from loguru import logger
from PIL import Image, ImageFile, ImageOps
from starlette.concurrency import run_in_threadpool

from ...core.config import Settings
from ...core.errors import AppError, ErrorCode
from ...core.ids import is_valid_id, new_id, utcnow
from ...core.session import same_owner
from ...infrastructure.storage import ImageStorage
from .model import UploadRecord
from .repository import UploadRepo
from .schemas import UploadResponse

JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
READ_CHUNK = 1 << 20

ImageFile.LOAD_TRUNCATED_IMAGES = False


def sniff(head: bytes) -> str | None:
    """'jpeg' | 'png' | None. Only magic bytes count; client filename / Content-Type are ignored."""
    if head.startswith(JPEG_MAGIC):
        return "jpeg"
    if head.startswith(PNG_MAGIC):
        return "png"
    return None


@dataclass(frozen=True)
class ProcessedImage:
    data: bytes
    width: int
    height: int
    kind: str  # jpeg | png

    @property
    def mime_type(self) -> str:
        return f"image/{self.kind}"

    @property
    def ext(self) -> str:
        return "jpg" if self.kind == "jpeg" else "png"


def process_image(raw: bytes, kind: str, max_pixels: int) -> ProcessedImage:
    """Decode for real, apply EXIF orientation, re-encode without EXIF/GPS/XMP/text chunks."""
    try:
        with Image.open(io.BytesIO(raw)) as im:
            fmt = (im.format or "").upper()
            if (kind == "jpeg" and fmt not in ("JPEG", "MPO")) or (kind == "png" and fmt != "PNG"):
                raise AppError(ErrorCode.IMAGE_DECODE_FAILED)
            w, h = im.size
            if w <= 0 or h <= 0:
                raise AppError(ErrorCode.IMAGE_DECODE_FAILED)
            if w * h > max_pixels:
                raise AppError(ErrorCode.IMAGE_TOO_LARGE)
            icc = im.info.get("icc_profile")
            im.load()
            oriented = ImageOps.exif_transpose(im)
    except AppError:
        raise
    except Image.DecompressionBombError as e:
        raise AppError(ErrorCode.IMAGE_TOO_LARGE) from e
    except Exception as e:  # PIL raises many types for corrupt / truncated data
        raise AppError(ErrorCode.IMAGE_DECODE_FAILED) from e

    oriented.info = {}
    out = io.BytesIO()
    if kind == "jpeg":
        if oriented.mode not in ("RGB", "L"):
            oriented = oriented.convert("RGB")
        oriented.save(out, "JPEG", quality=95, icc_profile=icc)
    else:
        if oriented.mode == "P":
            oriented = oriented.convert("RGBA" if "transparency" in im.info else "RGB")
        elif oriented.mode not in ("RGB", "RGBA", "L", "LA"):
            oriented = oriented.convert("RGB")
        oriented.save(out, "PNG", icc_profile=icc)
    return ProcessedImage(out.getvalue(), oriented.width, oriented.height, kind)


class UploadService:
    def __init__(self, settings: Settings, storage: ImageStorage, uploads: UploadRepo) -> None:
        self.settings = settings
        self.storage = storage
        self.uploads = uploads

    def image_url(self, image_id: str) -> str:
        return f"{self.settings.api_v1}/uploads/{image_id}/image"

    def to_response(self, rec: UploadRecord) -> UploadResponse:
        return UploadResponse(image_id=rec.image_id, width=rec.width, height=rec.height, mime_type=rec.mime_type,
                              byte_size=rec.byte_size, image_url=self.image_url(rec.image_id),
                              created_at=rec.created_at, expires_at=rec.expires_at)

    async def _read_limited(self, file: UploadFile) -> bytes:
        limit = self.settings.MAX_UPLOAD_BYTES
        buf = bytearray()
        while chunk := await file.read(READ_CHUNK):
            if not buf and sniff(chunk[:8]) is None:
                raise AppError(ErrorCode.UNSUPPORTED_IMAGE)
            buf += chunk
            if len(buf) > limit:
                raise AppError(ErrorCode.IMAGE_TOO_LARGE)
        return bytes(buf)

    async def create(self, owner: str, file: UploadFile) -> UploadResponse:
        raw = await self._read_limited(file)
        kind = sniff(raw[:8])
        if kind is None:
            raise AppError(ErrorCode.UNSUPPORTED_IMAGE)
        img = await run_in_threadpool(process_image, raw, kind, self.settings.MAX_IMAGE_PIXELS)
        now = utcnow()
        image_id = new_id("img")
        key = ImageStorage.key_for(image_id, img.ext)
        rec = UploadRecord(
            image_id=image_id, owner_session_hash=owner, storage_key=key, mime_type=img.mime_type,
            byte_size=len(img.data), width=img.width, height=img.height,
            sha256=hashlib.sha256(raw).hexdigest(), created_at=now,
            expires_at=now + timedelta(hours=self.settings.IMAGE_RETENTION_HOURS),
        )
        await run_in_threadpool(self.storage.write, key, img.data)
        try:
            await self.uploads.insert(rec)
        except BaseException:
            self.storage.delete(key)
            raise
        logger.info("upload created image_id={} {}x{} {}", image_id, img.width, img.height, img.kind)
        return self.to_response(rec)

    async def get_owned(self, owner: str, image_id: str) -> UploadRecord:
        rec = await self.uploads.get(image_id) if is_valid_id(image_id, "img") else None
        if rec is None or not same_owner(rec.owner_session_hash, owner):
            raise AppError(ErrorCode.NOT_FOUND)
        return rec

    @staticmethod
    def is_expired(rec: UploadRecord | None) -> bool:
        return rec is None or rec.expired or rec.expires_at <= utcnow()

    async def image_file(self, owner: str, image_id: str) -> tuple[Path, str]:
        rec = await self.get_owned(owner, image_id)
        if self.is_expired(rec) or not self.storage.exists(rec.storage_key):
            raise AppError(ErrorCode.IMAGE_EXPIRED)
        return self.storage.path(rec.storage_key), rec.mime_type

    async def acquire_reference(self, owner: str, image_id: str) -> UploadRecord:
        rec = await self.uploads.acquire(image_id, owner, utcnow())
        if rec is None:
            raise AppError(ErrorCode.IMAGE_EXPIRED)
        return rec

    async def release_reference(self, image_id: str) -> None:
        """Drop one inspection reference; the last one removes the upload record and its file."""
        rec = await self.uploads.release(image_id)
        if rec is not None and rec.reference_count <= 0 and await self.uploads.delete_unreferenced(image_id):
            self.storage.delete(rec.storage_key)
            logger.info("upload removed (no references) image_id={}", image_id)

    async def delete(self, owner: str, image_id: str) -> None:
        rec = await self.get_owned(owner, image_id)
        if rec.reference_count > 0 or not await self.uploads.delete_unreferenced(image_id):
            raise AppError(ErrorCode.IMAGE_IN_USE)
        self.storage.delete(rec.storage_key)
        logger.info("upload deleted image_id={}", image_id)


def get_upload_service(request: Request) -> UploadService:
    return request.app.state.container.upload_service
