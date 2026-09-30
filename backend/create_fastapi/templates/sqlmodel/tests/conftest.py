import pytest
import shutil
from typing import AsyncGenerator
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlmodel import SQLModel

from apiapp.run import create_app
from apiapp.core.config import get_settings, Settings
from apiapp.infrastructure.database import db_client


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for the session.
    """
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def settings() -> Settings:
    """
    Load settings for tests.
    We override DATABASE_URI to ensure tests have a connection.
    """
    settings = get_settings()
    if not settings.DATABASE_URI:
        settings.DATABASE_URI = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"
    return settings


@pytest.fixture(scope="session")
async def app() -> AsyncGenerator[FastAPI, None]:
    """
    Create a FastAPI application instance for the test session.
    We use LifespanManager to ensure startup/shutdown events run.
    """
    _app = create_app()
    async with LifespanManager(_app):
        yield _app


@pytest.fixture(scope="function")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """
    Create a test client for the FastAPI application.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture(scope="function", autouse=True)
async def clean_db(settings: Settings):
    """
    Clean the database before each test function.
    This ensures a fresh state for every test.
    """
    if "test" not in settings.APP_ENV:
        pytest.skip("Running against a non-test database! Aborting.")

    if db_client.engine:
        # Drop all tables and recreate them
        async with db_client.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.run_sync(SQLModel.metadata.create_all)

    yield
