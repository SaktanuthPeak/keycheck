"""
Attachment use case - business logic and data access
Simplified pattern using BaseUseCase for common CRUD operations
"""

from fastapi import Depends, UploadFile, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
import uuid

from .model import Attachment
from .schemas import CreateAttachment, UpdateAttachment, AttachmentResponse
from ...core.base_use_case import BaseUseCase
from ...infrastructure.database import get_db_session
from ...infrastructure.file_storage import File


class AttachmentUseCase(BaseUseCase[Attachment, CreateAttachment, UpdateAttachment, AttachmentResponse]):
    """
    Attachment use case handling both business logic and data access.
    Inherits common CRUD operations from BaseUseCase.
    """

    model = Attachment
    response_schema = AttachmentResponse

    async def upload_attachment(self, file: UploadFile, user_id: uuid.UUID) -> AttachmentResponse:
        """Upload a file to storage and register in DB"""
        # Determine file size
        file.file.seek(0, 2)
        size_bytes = file.file.tell()
        file.file.seek(0)

        # Save to storage
        new_file = File(collection_name="attachments")
        file_id = await new_file.put(file)

        # Save to database
        attachment_db = Attachment(
            id=uuid.uuid4(),
            filename=file.filename or "unknown",
            file_id=file_id,
            content_type=file.content_type or "application/octet-stream",
            size_bytes=size_bytes,
            uploaded_by_id=user_id,
        )
        self.session.add(attachment_db)
        await self.session.commit()
        await self.session.refresh(attachment_db)
        return self._to_response(attachment_db)

    async def get_attachment_file_info(self, doc_id: str) -> tuple[str, str, str] | None:
        """Get file path, filename, and content_type of attachment"""
        try:
            parsed_id = uuid.UUID(doc_id)
        except ValueError:
            return None

        attachment = await self.session.get(Attachment, parsed_id)
        if not attachment:
            return None

        storage_file = File(collection_name="attachments", file_id=attachment.file_id)
        return storage_file.get_path(), attachment.filename, attachment.content_type

    async def delete(self, doc_id: str) -> bool:
        """Delete attachment from DB and storage"""
        try:
            parsed_id = uuid.UUID(doc_id)
        except ValueError:
            return False

        attachment = await self.session.get(Attachment, parsed_id)
        if not attachment:
            return False

        # Delete physical file
        try:
            storage_file = File(collection_name="attachments", file_id=attachment.file_id)
            await storage_file.delete()
        except Exception:
            pass

        # Delete database record
        await self.session.delete(attachment)
        await self.session.commit()
        return True


# Dependency injection
def get_attachment_use_case(session: AsyncSession = Depends(get_db_session)) -> AttachmentUseCase:
    """Get AttachmentUseCase instance"""
    return AttachmentUseCase(session)