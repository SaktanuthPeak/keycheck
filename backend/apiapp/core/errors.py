"""Error contract (Spec §11.5, api-contract §3): {"error": {code, message, retryable}}; never a stack trace."""

from enum import StrEnum

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse


class ErrorCode(StrEnum):
    UNSUPPORTED_IMAGE = "UNSUPPORTED_IMAGE"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
    IMAGE_DECODE_FAILED = "IMAGE_DECODE_FAILED"
    INVALID_CORNERS = "INVALID_CORNERS"
    LAYOUT_NOT_FOUND = "LAYOUT_NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    IMAGE_EXPIRED = "IMAGE_EXPIRED"
    IMAGE_IN_USE = "IMAGE_IN_USE"
    INSPECTION_IN_PROGRESS = "INSPECTION_IN_PROGRESS"
    QUEUE_FULL = "QUEUE_FULL"
    ORIGIN_FORBIDDEN = "ORIGIN_FORBIDDEN"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    LAYOUT_MISMATCH = "LAYOUT_MISMATCH"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# code -> (http status, default Thai message, retryable)
ERROR_SPECS: dict[ErrorCode, tuple[int, str, bool]] = {
    ErrorCode.UNSUPPORTED_IMAGE: (415, "รองรับเฉพาะไฟล์ภาพ JPEG หรือ PNG", True),
    ErrorCode.IMAGE_TOO_LARGE: (413, "ไฟล์ภาพใหญ่เกินกำหนด กรุณาใช้ภาพที่เล็กลง", True),
    ErrorCode.IMAGE_DECODE_FAILED: (422, "เปิดไฟล์ภาพไม่ได้ ไฟล์อาจเสียหาย กรุณาถ่ายหรือเลือกภาพใหม่", True),
    ErrorCode.INVALID_CORNERS: (422, "กรุณาเลือกจุดอ้างอิงใหม่ตามลำดับ Q → P → M → Z", True),
    ErrorCode.LAYOUT_NOT_FOUND: (422, "ไม่พบ Layout ที่เลือก", False),
    ErrorCode.VALIDATION_ERROR: (422, "ข้อมูลที่ส่งมาไม่ถูกต้อง", False),
    ErrorCode.NOT_FOUND: (404, "ไม่พบข้อมูลที่ขอ", False),
    ErrorCode.IMAGE_EXPIRED: (410, "ภาพนี้ถูกลบตามระยะเวลาเก็บข้อมูลแล้ว กรุณาอัปโหลดภาพใหม่", False),
    ErrorCode.IMAGE_IN_USE: (409, "ลบภาพไม่ได้เพราะมีผลตรวจที่ใช้ภาพนี้อยู่", False),
    ErrorCode.INSPECTION_IN_PROGRESS: (409, "ลบไม่ได้ระหว่างที่ระบบกำลังตรวจ กรุณารอให้เสร็จก่อน", True),
    ErrorCode.QUEUE_FULL: (429, "ขณะนี้มีงานตรวจรออยู่มาก กรุณาลองใหม่อีกครั้งในภายหลัง", True),
    ErrorCode.ORIGIN_FORBIDDEN: (403, "คำขอนี้ไม่ได้มาจากหน้าเว็บที่อนุญาต", False),
    ErrorCode.MODEL_UNAVAILABLE: (503, "ระบบตรวจยังไม่พร้อมใช้งาน กรุณาลองใหม่ภายหลัง", True),
    ErrorCode.LAYOUT_MISMATCH: (
        422,
        "ตำแหน่งปุ่มไม่ตรงกับ Layout มาตรฐาน กรุณาแตะจุดอ้างอิงใหม่ หรือคีย์บอร์ดรุ่นนี้อาจไม่รองรับ",
        True,
    ),
    ErrorCode.PROCESSING_FAILED: (500, "ประมวลผลไม่สำเร็จ กรุณาลองใหม่อีกครั้ง", True),
    ErrorCode.INTERNAL_ERROR: (500, "เกิดข้อผิดพลาดภายในระบบ", True),
}

_STATUS_TO_CODE = {
    404: ErrorCode.NOT_FOUND,
    413: ErrorCode.IMAGE_TOO_LARGE,
    415: ErrorCode.UNSUPPORTED_IMAGE,
    429: ErrorCode.QUEUE_FULL,
}


def error_body(code: ErrorCode | str, message: str | None = None, retryable: bool | None = None) -> dict:
    code = ErrorCode(code)
    _, default_msg, default_retry = ERROR_SPECS[code]
    return {
        "code": code.value,
        "message": message or default_msg,
        "retryable": default_retry if retryable is None else retryable,
    }


class AppError(StarletteHTTPException):
    """The single application exception; subclasses HTTPException so FastAPI body parsing re-raises it untouched."""

    def __init__(self, code: ErrorCode, message: str | None = None, *, retryable: bool | None = None,
                 status_code: int | None = None) -> None:
        self.code = ErrorCode(code)
        self.body = error_body(self.code, message, retryable)
        super().__init__(status_code or ERROR_SPECS[self.code][0], self.body["message"])


def error_response(code: ErrorCode, message: str | None = None, *, status_code: int | None = None,
                   headers: dict | None = None) -> JSONResponse:
    return JSONResponse({"error": error_body(code, message)}, status_code=status_code or ERROR_SPECS[code][0],
                        headers=headers)


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse({"error": exc.body}, status_code=exc.status_code)


async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code >= 500:
        code = ErrorCode.INTERNAL_ERROR
    else:
        code = _STATUS_TO_CODE.get(exc.status_code, ErrorCode.VALIDATION_ERROR)
    return JSONResponse({"error": error_body(code)}, status_code=exc.status_code,
                        headers=getattr(exc, "headers", None))


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    corners_only = bool(errors) and all("reference_points_normalized" in e.get("loc", ()) for e in errors)
    code = ErrorCode.INVALID_CORNERS if corners_only else ErrorCode.VALIDATION_ERROR
    return JSONResponse({"error": error_body(code)}, status_code=422)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.opt(exception=exc).error("unhandled error on {} {}", request.method, request.url.path)
    return JSONResponse({"error": error_body(ErrorCode.INTERNAL_ERROR)}, status_code=500)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)


# OpenAPI: describe the error envelope for generated clients.
ERROR_RESPONSE_SCHEMA = {
    "description": "Error",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "required": ["error"],
                "properties": {
                    "error": {
                        "type": "object",
                        "required": ["code", "message", "retryable"],
                        "properties": {
                            "code": {"type": "string", "enum": [c.value for c in ErrorCode]},
                            "message": {"type": "string"},
                            "retryable": {"type": "boolean"},
                        },
                    }
                },
            }
        }
    },
}
