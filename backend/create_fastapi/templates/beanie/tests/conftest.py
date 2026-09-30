import pytest
import shutil
from typing import AsyncGenerator, Generator
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from pymongo import AsyncMongoClient
from asgi_lifespan import LifespanManager

from apiapp.run import create_app
from apiapp.core.config import get_settings, Settings
from apiapp.infrastructure.database import beanie_client


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
        settings.DATABASE_URI = "mongodb://localhost:27017/test_db"
    return settings


@pytest.fixture(scope="session")
async def db_client(settings: Settings) -> AsyncGenerator[AsyncMongoClient, None]:
    """
    Create a MongoDB client for the test session.
    """
    client = AsyncMongoClient(settings.DATABASE_URI)
    yield client
    await client.close()


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
async def clean_db(settings: Settings, db_client: AsyncMongoClient):
    """
    Clean the database before each test function.
    This ensures a fresh state for every test.
    Instead of dropping the whole database, we can just clear collections,
    but for simplicity/speed with small tests, we might not need to drop everything if we randomise IDs.
    However, for reliable tests, cleaning is best.
    """
    # Assuming the database name is part of the URI or default
    db_name = db_client.get_default_database().name
    # If we want to be safe and only run on a test database:
    if "test" not in db_name and "test" not in settings.APP_ENV:
        pytest.skip("Running against a non-test database! Aborting.")

    # Option 1: Drop the database (slow but clean)
    # await db_client.drop_database(db_name)

    # Option 2: Delete all documents from all collections (faster often)
    db = db_client[db_name]
    collections = await db.list_collection_names()
    for collection in collections:
        await db[collection].delete_many({})

    yield
