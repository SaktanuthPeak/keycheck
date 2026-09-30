---
trigger: always_on
---

# Testing Guide

This project uses `pytest` and `pytest-asyncio` for unit and integration testing of the FastAPI application.

## Prerequisites

- Python 3.12+
- MongoDB running locally on `localhost:27017` (or configured via `DATABASE_URI` environment variable for tests)

## Running Tests

1. Ensure your virtual environment is activated:
   ```bash
   source venv/bin/activate
   ```

2. Run all tests with verbosity:
   ```bash
   pytest tests/ -v
   ```

## Testing Strategy & Best Practices

The application is structured using the **Router & UseCase** pattern. To keep unit tests isolated, fast, and independent of the actual MongoDB instance for routing tests, we heavily rely on **Dependency Injection Mocking**.

### 1. Mocking Dependencies
Instead of hitting the real database and executing live business logic, we isolate the `APIRouter` by overriding the `UseCase` dependency with `unittest.mock.AsyncMock`.

**Example Pattern:**
```python
from unittest.mock import AsyncMock
from httpx import AsyncClient
import pytest
from fastapi_pagination import Page

@pytest.fixture
def mock_use_case():
    mock_case = AsyncMock()
    mock_case.search.return_value = Page(items=[...], total=1, page=1, size=50)
    mock_case.get_by_id.return_value = {...}
    return mock_case

@pytest.mark.asyncio
async def test_get_resource(client: AsyncClient, app, mock_use_case):
    # Override the dependency
    app.dependency_overrides[get_my_use_case] = lambda: mock_use_case
    
    # Execute the request
    response = await client.get("/v1/my-resource/")
    
    # Verify the results
    assert response.status_code == 200
    
    # Clean up the override
    app.dependency_overrides.pop(get_my_use_case, None)
```

### 2. Pydantic Models & Beanie Documents
When testing models directly, ensure `beanie` collections are initialized via the application's lifespan events. To achieve this, inject the `app` or `client` fixture into your tests which handles the database initialization seamlessly.

### 3. Database Management (`conftest.py`)
- `tests/conftest.py` sets up global instances:
  - `app`: Provides the FastAPI instance bound with a `LifespanManager` (to initialize DB models like `InitBeanie`).
  - `client`: Provides `httpx.AsyncClient` along with authentication bypasses `mock_current_user` for endpoints depending on authentication.
- **Data Cleanup**: Between tests, `clean_db` deletes documents across collections to avoid corrupted states for actual integration tests.

## Test Directory Structure

```text
tests/
├── conftest.py                   # Core fixtures and DB resets
├── test_health.py                # Server health check endpoint tests
├── test_user_unit.py             # Schema and model validation tests
└── test_[module_name]_api.py     # Endpoint behavior tests for respective modules
```