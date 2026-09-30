"""
Base use case - Generic CRUD operations for Beanie documents
Provides common CRUD functionality to reduce code duplication
"""

from datetime import datetime, timezone
from typing import Generic, TypeVar, Optional, Type

from beanie import Document, PydanticObjectId
from fastapi_pagination import Page
from fastapi_pagination.ext.beanie import paginate
from pydantic import BaseModel


# Type variables for generic types
ModelType = TypeVar("ModelType", bound=Document)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=BaseModel)


class BaseUseCase(
    Generic[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]
):
    """
    Base use case with generic CRUD operations.

    Usage:
        class PetUseCase(BaseUseCase[Pet, CreatePet, UpdatePet, PetResponse]):
            model = Pet
            response_schema = PetResponse
    """

    model: Type[ModelType]
    response_schema: Type[ResponseSchemaType]

    # ==================== Create Operations ====================

    async def create(self, data: CreateSchemaType) -> ResponseSchemaType:
        """Create a new document"""
        doc = self.model(
            **data.model_dump(),
            created_at=datetime.now(timezone.utc),
        )
        await doc.insert()
        return self._to_response(doc)

    # ==================== Read Operations ====================

    async def get_by_id(self, doc_id: str) -> Optional[ResponseSchemaType]:
        """Get document by ID"""
        doc = await self.model.get(PydanticObjectId(doc_id))
        return self._to_response(doc) if doc else None

    async def get_list(self) -> Page[ResponseSchemaType]:
        """Get paginated list of documents"""
        find_query = self.model.find_all().sort("-created_at")
        page = await paginate(find_query)
        return self._page_to_response(page)

    # ==================== Update Operations ====================

    async def update(
        self, doc_id: str, data: UpdateSchemaType
    ) -> Optional[ResponseSchemaType]:
        """Update document with validation"""
        doc = await self.model.get(PydanticObjectId(doc_id))
        if not doc:
            return None

        update_data = data.model_dump(exclude_none=True)

        # Update fields
        for key, value in update_data.items():
            setattr(doc, key, value)

        # Update timestamp if model has updated_at field
        if hasattr(doc, "updated_at"):
            setattr(doc, "updated_at", datetime.now(timezone.utc))

        await doc.save()

        return self._to_response(doc)

    # ==================== Delete Operations ====================

    async def delete(self, doc_id: str) -> bool:
        """Delete document by ID"""
        doc = await self.model.get(PydanticObjectId(doc_id))
        if not doc:
            return False

        await doc.delete()
        return True

    # ==================== Protected Helper Methods ====================

    def _to_response(self, doc: ModelType) -> ResponseSchemaType:
        """Convert Document model to Response schema"""
        return self.response_schema.model_validate(doc.model_dump())

    def _page_to_response(self, page: Page[ModelType]) -> Page[ResponseSchemaType]:
        """Convert paginated Documents to paginated Response schemas"""
        return Page(
            items=[self._to_response(doc) for doc in page.items],
            total=page.total,
            page=page.page,
            size=page.size,
            pages=page.pages,
        )
