"""
Hospital use case - business logic and data access
Simplified pattern using BaseUseCase for common CRUD operations
"""

from .model import Hospital
from .schemas import CreateHospital, UpdateHospital, HospitalResponse
from ...core.base_use_case import BaseUseCase
from fastapi_pagination import Page


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
        from beanie.operators import In
        from fastapi_pagination.ext.beanie import paginate
        
        query = self.model.find(In(self.model.services, [service_name]))
        page = await paginate(query)
        return self._page_to_response(page)


# Dependency injection
def get_hospital_use_case() -> HospitalUseCase:
    """Get HospitalUseCase instance"""
    return HospitalUseCase()