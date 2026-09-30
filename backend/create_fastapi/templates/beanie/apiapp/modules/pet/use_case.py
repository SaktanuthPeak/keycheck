"""
Pet use case - business logic and data access
Simplified pattern using Beanie's built-in methods directly
"""

from fastapi import HTTPException, status, UploadFile
from fastapi.responses import StreamingResponse
from fastapi_pagination import Page
from fastapi_pagination.ext.beanie import paginate
from beanie import PydanticObjectId

from .model import Pet
from .schemas import CreatePet, UpdatePet, PetResponse, PetListProjection
from ...core.base_use_case import BaseUseCase
from ..user.model import User
from ...infrastructure.gridfs import File


class PetUseCase(BaseUseCase[Pet, CreatePet, UpdatePet, PetResponse]):
    """
    Pet use case handling both business logic and data access.
    Inherits common CRUD operations from BaseUseCase.
    """

    model = Pet
    response_schema = PetResponse

    # Add custom business logic here if needed
    # For example:
    # async def get_by_name(self, name: str) -> Optional[PetResponse]:
    #     """Custom query for finding pet by name"""
    #     pet = await Pet.find_one({"name": name})
    #     return self._to_response(pet) if pet else None

    # ==================== Custom Create Logic ====================
    async def create(self, data: CreatePet) -> PetResponse:
        """Create a new dog and link to owner"""
        # 1. Fetch the user safely to make sure they exist
        owner = await User.get(data.owner_id)
        if not owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Owner not found"
            )
        
        # 2. Extract out the raw dict excluding the relational id from Create Schema
        pet_data = data.model_dump()
        pet_data.pop("owner_id", None)
        
        # 3. Create Pet object and inject the owner object as the `Link`
        doc = self.model(
            **pet_data,
            owner=owner, # Pydantic/Beanie handles linking internally
        )
        await doc.insert()
        return self._to_response(doc)

    async def get_by_id(self, doc_id: str) -> PetResponse | None:
        """Example: Overriding standard get_by_id to show HOW TO properly fetch the Link"""
        # When fetching one single item by ID, `fetch_links=True` is quite acceptable and common
        doc = await self.model.get(PydanticObjectId(doc_id), fetch_links=True)
        return self._to_response(doc) if doc else None

    # ==================== Example of using Projection over fetch_links ====================
    async def get_list(self) -> Page[PetResponse]:
        """
        Get paginated list of documents USING PROJECTION instead of fetch_links=True.
        We then perform an In-Memory Batch Fetch to obtain the related users and map their names.
        """
        # Parse exactly what we want using `.project(Model)`
        find_query = self.model.find_all().sort("-created_at").project(PetListProjection)
        
        # Paginate naturally handles projected Beanie queries out of the box
        page = await paginate(find_query)
        
        # 1. Collect unique owner IDs from the current page
        owner_ids = list({doc.owner_id for doc in page.items if doc.owner_id})
        
        # 2. Fetch all required users in one query (Batch Fetching)
        user_map = {}
        if owner_ids:
            users = await User.find({"_id": {"$in": owner_ids}}).to_list()
            user_map = {str(u.id): u for u in users}
            
        # 3. Transform items and inject owner info before validation
        response_items = []
        for doc in page.items:
            doc_data = doc.model_dump()
            owner_id_str = str(doc.owner_id) if doc.owner_id else None
            
            if owner_id_str and owner_id_str in user_map:
                doc_data["owner_name"] = user_map[owner_id_str].name
                doc_data["owner_username"] = user_map[owner_id_str].username
                
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
        pet = await self.model.get(PydanticObjectId(entity_id))
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
        await pet.save()

        return self._to_response(pet)

    async def get_image(self, entity_id: str) -> StreamingResponse:
        """Get pet image stream."""
        pet = await self.model.get(PydanticObjectId(entity_id))
        if not pet or not pet.image_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
            )

        try:
            grid_file = File(collection_name="pets", file_id=pet.image_id)
            grid_out = await grid_file.get()
            
            async def file_iterator():
                while True:
                    chunk = await grid_out.readchunk()
                    if not chunk:
                        break
                    yield chunk

            content_type = "application/octet-stream"
            if grid_out.metadata and "content_type" in grid_out.metadata:
                content_type = grid_out.metadata["content_type"]

            return StreamingResponse(file_iterator(), media_type=content_type)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image not found in GridFS"
            )

    async def delete_image(self, entity_id: str) -> PetResponse:
        """Delete pet image."""
        pet = await self.model.get(PydanticObjectId(entity_id))
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
        await pet.save()

        return self._to_response(pet)


# Dependency injection
def get_pet_use_case() -> PetUseCase:
    """Get PetUseCase instance"""
    return PetUseCase()
