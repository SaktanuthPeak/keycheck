from fastapi import APIRouter, Depends

from .schemas import HealthCheckResponse
from .use_case import HealthService, get_health_service

router = APIRouter(prefix="/v1/health", tags=["Health"])


@router.get("", summary="Health Check")
async def health_check(service: HealthService = Depends(get_health_service)) -> HealthCheckResponse:
    """API, database and model readiness (no secrets)."""
    return await service.check()
