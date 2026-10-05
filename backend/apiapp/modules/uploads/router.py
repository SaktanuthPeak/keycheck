from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from fastapi.responses import FileResponse

from ...core.errors import ERROR_RESPONSE_SCHEMA
from ...core.session import get_owner
from .schemas import UploadResponse
from .use_case import UploadService, get_upload_service

router = APIRouter(prefix="/v1/uploads", tags=["Uploads"],
                   responses={code: ERROR_RESPONSE_SCHEMA for code in (403, 404, 409, 410, 413, 415, 422, 500)})


@router.post("", status_code=status.HTTP_201_CREATED, summary="Upload a keyboard photo")
async def create_upload(
    image: UploadFile = File(...),
    owner: str = Depends(get_owner),
    service: UploadService = Depends(get_upload_service),
) -> UploadResponse:
    return await service.create(owner, image)


@router.get(
    "/{image_id}/image",
    summary="Oriented image (EXIF applied and stripped)",
    response_class=FileResponse,
    responses={200: {"content": {"image/jpeg": {}, "image/png": {}}}},
)
async def get_upload_image(
    image_id: str,
    owner: str = Depends(get_owner),
    service: UploadService = Depends(get_upload_service),
) -> FileResponse:
    path, mime = await service.image_file(owner, image_id)
    return FileResponse(path, media_type=mime,
                        headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"})


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an unreferenced upload")
async def delete_upload(
    image_id: str,
    owner: str = Depends(get_owner),
    service: UploadService = Depends(get_upload_service),
) -> Response:
    await service.delete(owner, image_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
