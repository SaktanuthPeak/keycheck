from fastapi import APIRouter, Depends, Query, Response, status

from ...core.errors import ERROR_RESPONSE_SCHEMA
from ...core.session import get_owner
from .schemas import Inspection, InspectionAccepted, InspectionCreate, InspectionList
from .use_case import InspectionService, get_inspection_service

router = APIRouter(prefix="/v1/inspections", tags=["Inspections"],
                   responses={code: ERROR_RESPONSE_SCHEMA for code in (403, 404, 409, 410, 422, 429, 500)})


@router.post("", status_code=status.HTTP_202_ACCEPTED, summary="Queue an inspection")
async def create_inspection(
    body: InspectionCreate,
    owner: str = Depends(get_owner),
    service: InspectionService = Depends(get_inspection_service),
) -> InspectionAccepted:
    return await service.create(owner, body)


@router.get("", summary="Inspections of this session, newest first")
async def list_inspections(
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None, max_length=256),
    owner: str = Depends(get_owner),
    service: InspectionService = Depends(get_inspection_service),
) -> InspectionList:
    return await service.list(owner, limit, cursor)


@router.get("/{inspection_id}", summary="Inspection status and result")
async def get_inspection(
    inspection_id: str,
    owner: str = Depends(get_owner),
    service: InspectionService = Depends(get_inspection_service),
) -> Inspection:
    return await service.get(owner, inspection_id)


@router.delete("/{inspection_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a finished inspection")
async def delete_inspection(
    inspection_id: str,
    owner: str = Depends(get_owner),
    service: InspectionService = Depends(get_inspection_service),
) -> Response:
    await service.delete(owner, inspection_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
