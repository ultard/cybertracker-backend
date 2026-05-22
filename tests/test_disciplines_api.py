"""Тесты публичных и админских эндпоинтов дисциплин."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_disciplines_returns_seeded_items(client: AsyncClient):
    response = await client.get("/api/disciplines")
    assert response.status_code == 200
    page = response.json()
    assert page["total"] >= 5
    assert len(page["items"]) >= 1
    assert "skip" in page and "limit" in page


@pytest.mark.asyncio
async def test_list_disciplines_pagination(client: AsyncClient):
    response = await client.get("/api/disciplines", params={"skip": 0, "limit": 2})
    assert response.status_code == 200
    page = response.json()
    assert len(page["items"]) <= 2
    assert page["limit"] == 2


@pytest.mark.asyncio
async def test_get_discipline_by_id(client: AsyncClient):
    listing = await client.get("/api/disciplines", params={"limit": 1})
    discipline_id = listing.json()["items"][0]["id"]

    response = await client.get(f"/api/disciplines/{discipline_id}")
    assert response.status_code == 200
    assert response.json()["id"] == discipline_id


@pytest.mark.asyncio
async def test_get_discipline_not_found(client: AsyncClient):
    response = await client.get("/api/disciplines/999999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_discipline_requires_admin(client: AsyncClient):
    response = await client.post(
        "/api/disciplines",
        json={"name": "Test Game", "description": "Desc"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_discipline_as_admin(client: AsyncClient, auth_headers: dict[str, str]):
    response = await client.post(
        "/api/disciplines",
        headers=auth_headers,
        json={"name": "Starcraft II", "description": "RTS classic"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Starcraft II"
    assert data["description"] == "RTS classic"
