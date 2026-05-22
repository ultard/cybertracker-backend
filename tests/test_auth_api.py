"""Интеграционные тесты эндпоинтов /api/auth."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login_flow(client: AsyncClient):
    register = await client.post(
        "/api/auth/register",
        json={
            "login": "player_one",
            "password": "password1",
            "first_name": "Иван",
            "last_name": "Иванов",
            "nickname": "ivan",
        },
    )
    assert register.status_code == 200
    body = register.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body
    assert "refresh_token" in body

    login = await client.post(
        "/api/auth/login",
        json={"login": "player_one", "password": "password1"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]


@pytest.mark.asyncio
async def test_register_duplicate_login_returns_409(client: AsyncClient):
    payload = {
        "login": "dup_user",
        "password": "password1",
        "first_name": "A",
        "last_name": "B",
        "nickname": "dup",
    }
    assert (await client.post("/api/auth/register", json=payload)).status_code == 200
    again = await client.post("/api/auth/register", json=payload)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "http_409"


@pytest.mark.asyncio
async def test_login_invalid_credentials_returns_401(client: AsyncClient):
    response = await client.post(
        "/api/auth/login",
        json={"login": "admin", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_admin_profile(client: AsyncClient, auth_headers: dict[str, str]):
    response = await client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["login"] == "admin"
    assert data["role"] == "admin"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_refresh_rotates_tokens(client: AsyncClient):
    login = await client.post(
        "/api/auth/login",
        json={"login": "admin", "password": "admin123"},
    )
    refresh_token = login.json()["refresh_token"]

    refreshed = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refreshed.status_code == 200
    new_pair = refreshed.json()
    assert new_pair["refresh_token"] != refresh_token
    assert new_pair["access_token"]
    assert new_pair["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_401(client: AsyncClient):
    response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": "invalid-token-value-xx"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_session(client: AsyncClient, auth_headers: dict[str, str]):
    login = await client.post(
        "/api/auth/login",
        json={"login": "admin", "password": "admin123"},
    )
    refresh_token = login.json()["refresh_token"]

    logout = await client.post(
        "/api/auth/logout",
        headers=auth_headers,
        json={"refresh_token": refresh_token},
    )
    assert logout.status_code == 200
    assert logout.json()["ok"] is True

    refresh_again = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_again.status_code == 401


@pytest.mark.asyncio
async def test_register_validation_error_returns_422(client: AsyncClient):
    response = await client.post(
        "/api/auth/register",
        json={
            "login": "ab",
            "password": "short",
            "first_name": "",
            "last_name": "X",
            "nickname": "x",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
