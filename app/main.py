from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from scalar_fastapi import AgentScalarConfig, get_scalar_api_reference
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.core.limiter import limiter
from app.db.base import Base
from app.db.seed import seed_admin, seed_disciplines, seed_roles
from app.db.session import async_session_factory, engine
from app.openapi import OPENAPI_TAGS
from app.routers import api_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_factory() as session:
        await seed_roles(session)
        await seed_disciplines(session)
        await seed_admin(session)
        await session.commit()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=("REST API для киберспорт-арены."),
        version="0.1.0",
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(_request: object, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": str(exc.detail)})

    app.add_middleware(SlowAPIMiddleware)  # ty: ignore[invalid-argument-type]
    app.add_middleware(
        CORSMiddleware,  # ty: ignore[invalid-argument-type]
        allow_origins=settings.parse_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api")

    @app.get("/scalar", include_in_schema=False)
    async def scalar_documentation():
        return get_scalar_api_reference(
            openapi_url=app.openapi_url,
            title=app.title,
            agent=AgentScalarConfig(disabled=True),
        )

    return app


app = create_app()
