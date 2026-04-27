from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from scalar_fastapi import AgentScalarConfig, get_scalar_api_reference
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.core.limiter import limiter
from app.db.base import Base
from app.db.seed import seed_admin, seed_disciplines
from app.db.session import async_session_factory, engine
from app.openapi import OPENAPI_TAGS
from app.routers import api_router
from app.schemas.error import ErrorEnvelope, ErrorInfo

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_factory() as session:
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

    def _request_id(request: Request) -> str | None:
        return request.headers.get("X-Request-ID")

    def _err(
        *,
        request: Request,
        status_code: int,
        code: str,
        message: str,
        details: object | None = None,
    ) -> JSONResponse:
        payload = ErrorEnvelope(
            error=ErrorInfo(
                code=code,
                message=message,
                details=details,
                request_id=_request_id(request),
            )
        ).model_dump()
        return JSONResponse(status_code=status_code, content=payload)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        code = f"http_{exc.status_code}"
        return _err(
            request=request,
            status_code=exc.status_code,
            code=code,
            message=message,
            details=None if isinstance(exc.detail, str) else exc.detail,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _err(
            request=request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="validation_error",
            message="Validation error",
            details=exc.errors(),
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return _err(
            request=request,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="rate_limited",
            message=str(exc.detail),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, _exc: Exception) -> JSONResponse:
        return _err(
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="internal_error",
            message="Internal server error",
        )

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
