"""
Hospital API router - REST endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page, Params

from .use_case import HospitalUseCase, get_hospital_use_case
from .schemas import CreateHospital, UpdateHospital, HospitalResponse


router = APIRouter(prefix="/v1/hospitals", tags=["Hospital"])


@router.get("", dependencies=[Depends(Params)], response_model=Page[HospitalResponse])
async def get_hospital_list(
    use_case: HospitalUseCase = Depends(get_hospital_use_case),
):
    """Get paginated list of hospital."""
    return await use_case.get_list()


@router.get("/search", dependencies=[Depends(Params)], response_model=Page[HospitalResponse])
async def search_hospitals_by_service(
    service: str,
    use_case: HospitalUseCase = Depends(get_hospital_use_case),
):
    """Search hospitals providing a specific service."""
    return await use_case.search_by_service(service)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=HospitalResponse)
async def create_hospital(
    data: CreateHospital,
    use_case: HospitalUseCase = Depends(get_hospital_use_case),
):
    """Create a new hospital."""
    return await use_case.create(data)


@router.get("/{entity_id}", response_model=HospitalResponse)
async def get_hospital(
    entity_id: str,
    use_case: HospitalUseCase = Depends(get_hospital_use_case),
):
    """Get hospital by ID."""
    result = await use_case.get_by_id(entity_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
    return result


@router.patch("/{entity_id}", response_model=HospitalResponse)
async def update_hospital(
    entity_id: str,
    data: UpdateHospital,
    use_case: HospitalUseCase = Depends(get_hospital_use_case),
):
    """Update hospital by ID."""
    result = await use_case.update(entity_id, data)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
    return result


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hospital(
    entity_id: str,
    use_case: HospitalUseCase = Depends(get_hospital_use_case),
):
    """Delete hospital by ID."""
    deleted = await use_case.delete(entity_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")