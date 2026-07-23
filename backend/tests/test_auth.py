import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "strongpass123",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "User created"
    assert "user_id" in data


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "dupuser",
        "email": "dup1@example.com",
        "password": "strongpass123",
    })
    response = await client.post("/api/v1/auth/register", json={
        "username": "dupuser",
        "email": "dup2@example.com",
        "password": "strongpass123",
    })
    assert response.status_code == 400
    assert "Username or email already exists" in response.text


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "loginuser",
        "email": "login@example.com",
        "password": "testpass123",
    })
    response = await client.post("/api/v1/auth/login", json={
        "username": "loginuser",
        "password": "testpass123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_with_email(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "emailuser",
        "email": "email-login@example.com",
        "password": "testpass123",
    })
    response = await client.post("/api/v1/auth/login", json={
        "username": "email-login@example.com",
        "password": "testpass123",
    })
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "emailuser"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "wrongpass",
        "email": "wrong@example.com",
        "password": "correctpass",
    })
    response = await client.post("/api/v1/auth/login", json={
        "username": "wrongpass",
        "password": "wrongpass",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "meuser",
        "email": "me@example.com",
        "password": "testpass123",
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "username": "meuser",
        "password": "testpass123",
    })
    token = login_resp.json()["access_token"]
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["username"] == "meuser"


@pytest.mark.asyncio
async def test_me_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "refreshuser",
        "email": "refresh@example.com",
        "password": "testpass123",
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "username": "refreshuser",
        "password": "testpass123",
    })
    refresh_token = login_resp.json()["refresh_token"]

    response = await client.post(f"/api/v1/auth/refresh?token={refresh_token}")
    assert response.status_code == 200
    assert "access_token" in response.json()
