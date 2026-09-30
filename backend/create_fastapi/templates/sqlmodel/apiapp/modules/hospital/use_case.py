"""
Hospital use case - business logic and data access
Simplified pattern using BaseUseCase for common CRUD operations
"""

from .model import Hospital
from .schemas import CreateHospital, UpdateHospital, HospitalResponse
from ...core.base_use_case import BaseUseCase
from fastapi_pagination import Page
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ...infrastructure.database import get_db_session

class HospitalUseCase(BaseUseCase[Hospital, CreateHospital, UpdateHospital, HospitalResponse]):
    """
    Hospital use case handling both business logic and data access.
    Inherits common CRUD operations from BaseUseCase.
    """

    model = Hospital
    response_schema = HospitalResponse

    # Add custom business logic here if needed
    async def search_by_service(self, service_name: str) -> Page[HospitalResponse]:
        """Find hospitals that provide a specific service."""
        from sqlmodel import select
        from fastapi_pagination.ext.sqlalchemy import paginate
        from sqlalchemy.dialects.postgresql import JSONB
        from sqlalchemy import cast
        
        # PostgreSQL JSONB specific search
        query = select(self.model).where(
            cast(self.model.services, JSONB).contains([service_name])
        )
        return await paginate(self.session, query, transformer=self._page_to_response_transformer)


# Dependency injection
def get_hospital_use_case(session: AsyncSession = Depends(get_db_session)) -> HospitalUseCase:
    """Get HospitalUseCase instance"""
    return HospitalUseCase(session)