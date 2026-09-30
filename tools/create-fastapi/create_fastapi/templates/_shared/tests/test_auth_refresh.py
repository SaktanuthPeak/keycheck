import asyncio

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio(loop_scope="session")
async def test_refresh_token_flow(client: AsyncClient):
    # Register
    register_payload = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "password123",
        "confirm_password": "password123",
        "name": "Test User",
    }
    response = await client.post("/v1/users/register", json=register_payload)
    # If user already exists, we might get 400, which is fine for login.
    if response.status_code != 201:
        assert response.status_code == 400
        # If 400, it might be "User already exists", which is fine.

    # Login
    login_data = {"username": "testuser", "password": "password123", "strategy": "cookies"}
    response = await client.post("/v1/auth/login", json=login_data)
    assert response.status_code == 200
    tokens = response.json()
    access_token = tokens["access_token"]

    # Get refresh token from cookie
    refresh_token_cookie = response.cookies.get("refresh_token")
    assert refresh_token_cookie is not None

    await asyncio.sleep(1.1)

    # Test 1: Refresh with Cookie
    response = await client.get(
        "/v1/auth/refresh_token", cookies={"refresh_token": refresh_token_cookie}
    )
    assert response.status_code == 200
    new_tokens = response.json()
    assert "access_token" in new_tokens
    assert new_tokens["access_token"] != access_token

    # Test 2: Refresh with Bearer Token (Simulating Mobile/API client)
    # First, let's get a refresh token in the body (mobile login usually returns it)
    login_data_mobile = {
        "username": "testuser",
        "password": "password123",
        "strategy": "jwt",
    }
    response = await client.post("/v1/auth/login", json=login_data_mobile)
    assert response.status_code == 200
    tokens_mobile = response.json()
    refresh_token_bearer = tokens_mobile["refresh_token"]
    assert refresh_token_bearer is not None

    await asyncio.sleep(1.1)

    response = await client.get(
        "/v1/auth/refresh_token",
        headers={"Authorization": f"Bearer {refresh_token_bearer}"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

    # Test 3: No token
    client.cookies.clear()
    refresh_token_bearer = None  # clear var
    response = await client.get("/v1/auth/refresh_token", headers={})
    assert response.status_code == 401


async def _register_and_login_jwt(
    client: AsyncClient, username: str, password: str = "password123"
) -> dict:
    register_payload = {
        "email": f"{username}@example.com",
        "username": username,
        "password": password,
        "confirm_password": password,
        "name": username,
    }
    response = await client.post("/v1/users/register", json=register_payload)
    assert response.status_code in (201, 400)

    response = await client.post(
        "/v1/auth/login",
        json={"username": username, "password": password, "strategy": "jwt"},
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio(loop_scope="session")
async def test_logout_denylists_refresh_token(client: AsyncClient):
    """Logout then refresh with the same token → 401."""
    tokens = await _register_and_login_jwt(client, "revoke_logout")
    refresh = tokens["refresh_token"]
    assert refresh is not None

    response = await client.post(
        "/v1/auth/logout",
        headers={"Authorization": f"Bearer {refresh}"},
    )
    assert response.status_code == 200

    response = await client.get(
        "/v1/auth/refresh_token",
        headers={"Authorization": f"Bearer {refresh}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_jwt_strategy_logout_via_bearer_still_denylists(client: AsyncClient):
    """jwt strategy logout via Bearer refresh still denylists."""
    tokens = await _register_and_login_jwt(client, "revoke_jwt_logout")
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]

    # Access still works after single-session logout (until expiry) — accepted.
    me = await client.get(
        "/v1/users/me", headers={"Authorization": f"Bearer {access}"}
    )
    assert me.status_code == 200

    logout = await client.post(
        "/v1/auth/logout",
        headers={"Authorization": f"Bearer {refresh}"},
    )
    assert logout.status_code == 200

    # Access may still work; refresh must not.
    refresh_resp = await client.get(
        "/v1/auth/refresh_token",
        headers={"Authorization": f"Bearer {refresh}"},
    )
    assert refresh_resp.status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_logout_all_revokes_access_and_refresh(client: AsyncClient):
    """logout-all then old access → 403; old refresh → 401."""
    tokens = await _register_and_login_jwt(client, "revoke_logout_all")
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]

    response = await client.post(
        "/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert response.status_code == 200

    me = await client.get(
        "/v1/users/me", headers={"Authorization": f"Bearer {access}"}
    )
    assert me.status_code == 403

    refresh_resp = await client.get(
        "/v1/auth/refresh_token",
        headers={"Authorization": f"Bearer {refresh}"},
    )
    assert refresh_resp.status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_password_change_revokes_tokens(client: AsyncClient):
    """password change then old access → 403; old refresh → 401."""
    password = "password123"
    tokens = await _register_and_login_jwt(client, "revoke_password", password=password)
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]

    response = await client.patch(
        "/v1/users/me/password",
        headers={"Authorization": f"Bearer {access}"},
        json={
            "old_password": password,
            "new_password": "newpassword123",
            "confirm_new_password": "newpassword123",
        },
    )
    assert response.status_code == 200

    me = await client.get(
        "/v1/users/me", headers={"Authorization": f"Bearer {access}"}
    )
    assert me.status_code == 403

    refresh_resp = await client.get(
        "/v1/auth/refresh_token",
        headers={"Authorization": f"Bearer {refresh}"},
    )
    assert refresh_resp.status_code == 401
