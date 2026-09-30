"""
Pet use case - business logic and data access
Simplified pattern using BaseUseCase for common CRUD operations
"""

import uuid
from fastapi import HTTPException, status, UploadFile, Depends
from fastapi.responses import FileResponse
from fastapi_pagination import Page
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_pagination.ext.sqlalchemy import paginate

from .model import Pet
from .schemas import CreatePet, UpdatePet, PetResponse
from ...core.base_use_case import BaseUseCase
from ..user.model import User
from ...infrastructure.file_storage import File
from ...infrastructure.database import get_db_session


class PetUseCase(BaseUseCase[Pet, CreatePet, UpdatePet, PetResponse]):
    """
    Pet use case handling both business logic and data access.
    Inherits common CRUD operations from BaseUseCase.
    """

    model = Pet
    response_schema = PetResponse

    # ==================== Custom Create Logic ====================
    async def create(self, data: CreatePet) -> PetResponse:
        """Create a new pet and link to owner"""
        owner = await self.session.get(User, data.owner_id)
        if not owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Owner not found"
            )
        
        pet_data = data.model_dump()
        
        doc = self.model(
            id=uuid.uuid4(),
            **pet_data,
        )
        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)
        return self._to_response(doc)

    async def get_by_id(self, doc_id: str) -> PetResponse | None:
        """Example: Overriding standard get_by_id to also return owner info"""
        try:
            parsed_id = uuid.UUID(doc_id)
        except ValueError:
            return None

        doc = await self.session.get(Pet, parsed_id)
        if not doc:
            return None

        response = self._to_response(doc)
        if doc.owner_id:
            owner = await self.session.get(User, doc.owner_id)
            if owner:
                response.owner_name = owner.name
                response.owner_username = owner.username
        
        return response

    # ==================== Example of Batch Fetching ====================
    async def get_list(self) -> Page[PetResponse]:
        """
        Get paginated list of documents USING Batch Fetching for owners.
        """
        find_query = select(self.model).order_by(self.model.created_at.desc())
        page = await paginate(self.session, find_query, transformer=lambda x: x) # Get models first
        
        # 1. Collect unique owner IDs from the current page
        owner_ids = list({doc.owner_id for doc in page.items if doc.owner_id})
        
        # 2. Fetch all required users in one query (Batch Fetching)
        user_map = {}
        if owner_ids:
            statement = select(User).where(User.id.in_(owner_ids))
            result = await self.session.exec(statement)
            users = result.all()
            user_map = {u.id: u for u in users}
            
        # 3. Transform items and inject owner info
        response_items = []
        for doc in page.items:
            doc_data = doc.model_dump()
            
            if doc.owner_id and doc.owner_id in user_map:
                doc_data["owner_name"] = user_map[doc.owner_id].name
                doc_data["owner_username"] = user_map[doc.owner_id].username
                
            response_items.append(self.response_schema.model_validate(doc_data))
        
        # Return transformed ResponseSchemaType
        return Page(
            items=response_items,
            total=page.total,
            page=page.page,
            size=page.size,
            pages=page.pages,
        )


    # ==================== Image Management ====================
    async def upload_image(self, entity_id: str, file: UploadFile) -> PetResponse:
        """Upload and link an image to a pet."""
        try:
            parsed_id = uuid.UUID(entity_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found"
            )

        pet = await self.session.get(Pet, parsed_id)
        if not pet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found"
            )

        if pet.image_id:
            try:
                old_file = File(collection_name="pets", file_id=pet.image_id)
                await old_file.delete()
            except Exception:
                pass

        new_file = File(collection_name="pets")
        file_id = await new_file.put(file)

        pet.image_id = file_id
        self.session.add(pet)
        await self.session.commit()
        await self.session.refresh(pet)

        return self._to_response(pet)

    async def get_image(self, entity_id: str) -> FileResponse:
        """Get pet image."""
        try:
            parsed_id = uuid.UUID(entity_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
            )

        pet = await self.session.get(Pet, parsed_id)
        if not pet or not pet.image_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
            )

        file = File(collection_name="pets", file_id=pet.image_id)
        if not file.file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image file missing"
            )

        return FileResponse(file.get_path())

    async def delete_image(self, entity_id: str) -> PetResponse:
        """Delete pet image."""
        try:
            parsed_id = uuid.UUID(entity_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
            )

        pet = await self.session.get(Pet, parsed_id)
        if not pet or not pet.image_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
            )

        try:
            grid_file = File(collection_name="pets", file_id=pet.image_id)
            await grid_file.delete()
        except Exception:
            pass

        pet.image_id = None
        self.session.add(pet)
        await self.session.commit()
        await self.session.refresh(pet)

        return self._to_response(pet)


# Dependency injection
def get_pet_use_case(session: AsyncSession = Depends(get_db_session)) -> PetUseCase:
    """Get PetUseCase instance"""
    return PetUseCase(session)
