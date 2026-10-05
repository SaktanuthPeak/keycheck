from fastapi import APIRouter, Depends

from .schemas import LayoutListResponse
from .use_case import LayoutService, get_layout_service

router = APIRouter(prefix="/v1/layouts", tags=["Layouts"])


@router.get("", summary="Supported layouts (internal_only excluded)")
async def list_layouts(service: LayoutService = Depends(get_layout_service)) -> LayoutListResponse:
    return await service.list_public()
