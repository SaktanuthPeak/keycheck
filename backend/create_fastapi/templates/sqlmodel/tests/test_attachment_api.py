import pytest
from httpx import AsyncClient
import io


@pytest.mark.asyncio(loop_scope="session")
async def test_attachment_lifecycle_and_auth(client: AsyncClient):
    # 1. Verify that upload without token fails (should return 401 Unauthorized)
    files = {"file": ("test.txt", b"Hello World from E2E Tests!", "text/plain")}
    response = await client.post("/v1/attachments/upload", files=files)
    assert response.status_code == 401

    # 2. Register user & login to get token
    register_payload = {
        "email": "user@test.com",
        "username": "usertest",
        "password": "password123",
        "confirm_password": "password123",
        "name": "User Test",
    }
    response = await client.post("/v1/users/register", json=register_payload)
    if response.status_code != 201:
        assert response.status_code == 400

    login_data = {"username": "usertest", "password": "password123", "strategy": "jwt"}
    response = await client.post("/v1/auth/login", json=login_data)
    assert response.status_code == 200
    tokens = response.json()
    access_token = tokens["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # 3. Upload file with authentication
    response = await client.post(
        "/v1/attachments/upload",
        files=files,
        headers=auth_headers
    )
    assert response.status_code == 201
    upload_res = response.json()
    assert "id" in upload_res
    assert upload_res["filename"] == "test.txt"
    assert upload_res["content_type"] == "text/plain"
    assert upload_res["size_bytes"] == len(b"Hello World from E2E Tests!")
    attachment_id = upload_res["id"]

    # 4. List attachments (authenticated)
    response = await client.get("/v1/attachments", headers=auth_headers)
    assert response.status_code == 200
    list_res = response.json()
    assert "items" in list_res
    assert len(list_res["items"]) >= 1
    assert any(item["id"] == attachment_id for item in list_res["items"])

    # 5. List attachments without auth (should fail)
    response = await client.get("/v1/attachments")
    assert response.status_code == 401

    # 6. Retrieve attachment details (authenticated)
    response = await client.get(f"/v1/attachments/{attachment_id}", headers=auth_headers)
    assert response.status_code == 200
    details_res = response.json()
    assert details_res["filename"] == "test.txt"

    # 7. Download attachment (public)
    response = await client.get(f"/v1/attachments/{attachment_id}/download")
    assert response.status_code == 200
    assert response.content == b"Hello World from E2E Tests!"
    assert response.headers["content-type"] == "text/plain; charset=utf-8"

    # 8. Delete attachment without authentication (should fail)
    response = await client.delete(f"/v1/attachments/{attachment_id}")
    assert response.status_code == 401

    # 9. Delete attachment with authentication (should succeed)
    response = await client.delete(f"/v1/attachments/{attachment_id}", headers=auth_headers)
    assert response.status_code == 204

    # 10. Verify deleted
    response = await client.get(f"/v1/attachments/{attachment_id}", headers=auth_headers)
    assert response.status_code == 404

    # 11. Download deleted file (should fail)
    response = await client.get(f"/v1/attachments/{attachment_id}/download")
    assert response.status_code == 404
