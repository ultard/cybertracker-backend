"""Тесты обработчиков ошибок и заголовка X-Request-ID."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_validation_error_envelope(client: AsyncClient):
    response = await client.post("/api/auth/login", json={"login": "x"})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"] is not None


@pytest.mark.asyncio
async def test_error_envelope_includes_request_id(client: AsyncClient):
    response = await client.get(
        "/api/disciplines/999999",
        headers={"X-Request-ID": "req-test-123"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["request_id"] == "req-test-123"


@pytest.mark.asyncio
async def test_unauthenticated_me_has_error_shape(client: AsyncClient):
    response = await client.get("/api/auth/me")
    assert "error" in response.json()
    assert "message" in response.json()["error"]
