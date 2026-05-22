"""Общие фикстуры: SQLite in-memory и HTTP-клиент FastAPI."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
from app.db.base import Base
from app.db.seed import seed_admin, seed_disciplines
from app.db.session import get_session
from app.main import create_app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_session() -> AsyncGenerator[AsyncSession]:
    async with test_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def _noop_lifespan(_app):
    yield


@pytest.fixture(scope="session", autouse=True)
async def _prepare_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with test_session_factory() as session:
        await seed_disciplines(session)
        await seed_admin(session)
        await session.commit()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    application = create_app()
    application.router.lifespan_context = _noop_lifespan
    application.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    application.dependency_overrides.clear()


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/auth/login",
        json={"login": "admin", "password": "admin123"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
