"""Health (Spec §11.2): API / DB / model readiness without secrets. Model state comes from the worker heartbeat."""

from fastapi import Request

from ...core.ids import utcnow
from ..model_bundles.repository import is_fresh
from .schemas import HealthCheckResponse


class HealthService:
    def __init__(self, container) -> None:
        self.c = container

    async def check(self) -> HealthCheckResponse:
        settings = self.c.settings
        if settings.memory_mode:
            database = "memory"
        else:
            database = "ok" if await self.c.db.ping() else "error"
        model, bundle_id = "unavailable", None
        if database != "error":
            st = await self.c.worker_status.latest()
            if is_fresh(st, utcnow(), settings.heartbeat_seconds):
                model, bundle_id = st.model_status, st.model_bundle_id
        ok = database in ("memory", "ok") and model == "ready"
        return HealthCheckResponse(status="ok" if ok else "degraded", api="ok", database=database, model=model,
                                   model_bundle_id=bundle_id)


def get_health_service(request: Request) -> HealthService:
    return HealthService(request.app.state.container)
