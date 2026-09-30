"""
Base use case - Generic CRUD operations for SQLModel models
Provides common CRUD functionality to reduce code duplication
"""

import uuid
from datetime import datetime, timezone
from typing import Generic, TypeVar, Optional, Type

from sqlmodel import SQLModel, select
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession


# Type variables for generic types
ModelType = TypeVar("ModelType", bound=SQLModel)
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

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== Create Operations ====================

    async def create(self, data: CreateSchemaType) -> ResponseSchemaType:
        """Create a new record"""
        doc = self.model(
            **data.model_dump(),
        )
        if hasattr(doc, "created_at"):
            doc.created_at = datetime.now(timezone.utc)
            
        if not hasattr(doc, "id") or doc.id is None:
            doc.id = uuid.uuid4()

        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)
        return self._to_response(doc)

    # ==================== Read Operations ====================

    async def get_by_id(self, doc_id: str) -> Optional[ResponseSchemaType]:
        """Get record by ID"""
        try:
            parsed_id = uuid.UUID(doc_id)
        except ValueError:
            return None
            
        doc = await self.session.get(self.model, parsed_id)
        return self._to_response(doc) if doc else None

    async def get_list(self) -> Page[ResponseSchemaType]:
        """Get paginated list of records"""
        find_query = select(self.model)
        if hasattr(self.model, "created_at"):
            find_query = find_query.order_by(self.model.created_at.desc())
            
        return await paginate(self.session, find_query, transformer=self._page_to_response_transformer)

    # ==================== Update Operations ====================

    async def update(
        self, doc_id: str, data: UpdateSchemaType
    ) -> Optional[ResponseSchemaType]:
        """Update record with validation"""
        try:
            parsed_id = uuid.UUID(doc_id)
        except ValueError:
            return None
            
        doc = await self.session.get(self.model, parsed_id)
        if not doc:
            return None

        update_data = data.model_dump(exclude_unset=True, exclude_none=True)

        # Update fields
        for key, value in update_data.items():
            setattr(doc, key, value)

        # Update timestamp if model has updated_at field
        if hasattr(doc, "updated_at"):
            setattr(doc, "updated_at", datetime.now(timezone.utc))

        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)

        return self._to_response(doc)

    # ==================== Delete Operations ====================

    async def delete(self, doc_id: str) -> bool:
        """Delete record by ID"""
        try:
            parsed_id = uuid.UUID(doc_id)
        except ValueError:
            return False
            
        doc = await self.session.get(self.model, parsed_id)
        if not doc:
            return False

        await self.session.delete(doc)
        await self.session.commit()
        return True

    # ==================== Protected Helper Methods ====================

    def _to_response(self, doc: ModelType) -> ResponseSchemaType:
        """Convert Model to Response schema"""
        return self.response_schema.model_validate(doc.model_dump())

    def _page_to_response_transformer(self, docs: list[ModelType]) -> list[ResponseSchemaType]:
        """Convert list of Models to list of Response schemas (for pagination)"""
        return [self._to_response(doc) for doc in docs]

    def _page_to_response(self, page: Page[ModelType]) -> Page[ResponseSchemaType]:
        """Convert paginated Models to paginated Response schemas"""
        return Page(
            items=[self._to_response(doc) for doc in page.items],
            total=page.total,
            page=page.page,
            size=page.size,
            pages=page.pages,
        )
