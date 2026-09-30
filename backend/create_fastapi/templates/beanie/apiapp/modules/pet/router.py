"""
Pet API router - REST endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi_pagination import Page, Params

from .use_case import PetUseCase, get_pet_use_case
from .schemas import CreatePet, UpdatePet, PetResponse


router = APIRouter(prefix="/v1/pets", tags=["Pet"])


@router.get("", dependencies=[Depends(Params)], response_model=Page[PetResponse])
async def get_pet_list(
    use_case: PetUseCase = Depends(get_pet_use_case),
):
    """Get paginated list of pet."""
    return await use_case.get_list()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PetResponse)
async def create_pet(
    data: CreatePet,
    use_case: PetUseCase = Depends(get_pet_use_case),
):
    """Create a new pet."""
    return await use_case.create(data)


@router.get("/{entity_id}", response_model=PetResponse)
async def get_pet(
    entity_id: str,
    use_case: PetUseCase = Depends(get_pet_use_case),
):
    """Get pet by ID."""
    result = await use_case.get_by_id(entity_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found"
        )
    return result


@router.patch("/{entity_id}", response_model=PetResponse)
async def update_pet(
    entity_id: str,
    data: UpdatePet,
    use_case: PetUseCase = Depends(get_pet_use_case),
):
    """Update pet by ID."""
    result = await use_case.update(entity_id, data)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found"
        )
    return result


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pet(
    entity_id: str,
    use_case: PetUseCase = Depends(get_pet_use_case),
):
    """Delete pet by ID."""
    deleted = await use_case.delete(entity_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found"
        )


@router.post("/{entity_id}/image", response_model=PetResponse)
async def upload_pet_image(
    entity_id: str,
    file: UploadFile = File(...),
    use_case: PetUseCase = Depends(get_pet_use_case),
):
    """Upload pet image."""
    return await use_case.upload_image(entity_id, file)


@router.get("/{entity_id}/image", response_class=StreamingResponse)
async def get_pet_image(
    entity_id: str,
    use_case: PetUseCase = Depends(get_pet_use_case),
):
    """Get pet image."""
    return await use_case.get_image(entity_id)


@router.delete("/{entity_id}/image", response_model=PetResponse)
async def delete_pet_image(
    entity_id: str,
    use_case: PetUseCase = Depends(get_pet_use_case),
):
    """Delete pet image."""
    return await use_case.delete_image(entity_id)
