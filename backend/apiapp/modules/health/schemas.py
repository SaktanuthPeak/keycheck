from typing import Literal

from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    status: Literal["ok", "degraded"]
    api: Literal["ok"]
    database: Literal["memory", "ok", "error"]
    model: Literal["loading", "ready", "error", "unavailable"]
    model_bundle_id: str | None = None
