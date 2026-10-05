from fastapi import FastAPI, Request
from loguru import logger
from starlette.responses import Response

from ..core.config import Settings
from ..core.errors import ErrorCode, error_response


def init_security_middleware(app: FastAPI, settings: Settings) -> None:
    """Initialize security middleware for user agent filtering"""

    @app.middleware("http")
    async def filter_user_agents(request: Request, call_next):
        user_agent = request.headers.get("user-agent", "")

        for agent in settings.DISALLOW_AGENTS:
            if agent in user_agent.lower():
                logger.warning("blocked user agent")
                return error_response(ErrorCode.VALIDATION_ERROR, "Client is not allowed.", status_code=406)

        response: Response = await call_next(request)
        return response
