"""
Attachment API router - REST endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, File as FastAPIFile, UploadFile
from fastapi.responses import FileResponse
from fastapi_pagination import Page, Params

from .use_case import AttachmentUseCase, get_attachment_use_case
from .schemas import CreateAttachment, UpdateAttachment, AttachmentResponse
import typing
from ...core.security import get_current_user


router = APIRouter(prefix="/v1/attachments", tags=["Attachment"])


@router.get("", dependencies=[Depends(Params)], response_model=Page[AttachmentResponse])
async def get_attachment_list(
    use_case: AttachmentUseCase = Depends(get_attachment_use_case),
    current_user: typing.Any = Depends(get_current_user),
):
    """Get paginated list of attachment."""
    return await use_case.get_list()


@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=AttachmentResponse)
async def upload_attachment(
    file: UploadFile = FastAPIFile(...),
    use_case: AttachmentUseCase = Depends(get_attachment_use_case),
    current_user: typing.Any = Depends(get_current_user),
):
    """Upload a new attachment."""
    return await use_case.upload_attachment(file, current_user.id)


@router.get("/{entity_id}", response_model=AttachmentResponse)
async def get_attachment(
    entity_id: str,
    use_case: AttachmentUseCase = Depends(get_attachment_use_case),
    current_user: typing.Any = Depends(get_current_user),
):
    """Get attachment by ID."""
    result = await use_case.get_by_id(entity_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return result


@router.get("/{entity_id}/download")
async def download_attachment(
    entity_id: str,
    use_case: AttachmentUseCase = Depends(get_attachment_use_case),
):
    """Download attachment by ID."""
    info = await use_case.get_attachment_file_info(entity_id)
    if not info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    file_path, filename, content_type = info
    import os
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Physical file not found")

    return FileResponse(path=file_path, filename=filename, media_type=content_type)


@router.patch("/{entity_id}", response_model=AttachmentResponse)
async def update_attachment(
    entity_id: str,
    data: UpdateAttachment,
    use_case: AttachmentUseCase = Depends(get_attachment_use_case),
    current_user: typing.Any = Depends(get_current_user),
):
    """Update attachment by ID."""
    result = await use_case.update(entity_id, data)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return result


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    entity_id: str,
    use_case: AttachmentUseCase = Depends(get_attachment_use_case),
    current_user: typing.Any = Depends(get_current_user),
):
    """Delete attachment by ID."""
    deleted = await use_case.delete(entity_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")