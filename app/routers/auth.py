from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.limiter import limiter
from app.core.security import (
    JWT_TYP_REFRESH,
    create_access_token,
    create_refresh_token_with_jti,
    hash_password,
    refresh_jti_hash,
    safe_decode_token,
    verify_password,
)
from app.deps import get_current_user, get_db
from app.models import RefreshSession, User
from app.models.enums import UserRoleName
from app.repositories import RoleRepository, UserRepository
from app.repositories.auth import RefreshSessionRepository
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserRead

router = APIRouter()
settings = get_settings()


def _to_user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        login=user.login,
        role_id=user.role_id,
        first_name=user.first_name,
        last_name=user.last_name,
        nickname=user.nickname,
        is_active=user.is_active,
    )


def _issue_token_pair(user: User) -> tuple[TokenResponse, str, datetime]:
    uid = str(user.id)
    refresh_token, refresh_jti, refresh_expires_at = create_refresh_token_with_jti(uid)
    return (
        TokenResponse(
            access_token=create_access_token(uid, extra={"role": user.role.name}),
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            refresh_expires_in=settings.refresh_token_expire_days * 24 * 60 * 60,
            user=_to_user_read(user),
        ),
        refresh_jti_hash(refresh_jti),
        refresh_expires_at,
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    summary="Регистрация",
    description="Создаёт учётную запись с ролью игрок и возвращает токены (auto-login).",
)
async def register(
    data: RegisterRequest, session: Annotated[AsyncSession, Depends(get_db)]
) -> TokenResponse:
    user_repository = UserRepository(session)
    role_repository = RoleRepository(session)
    if await user_repository.get_by_login(data.login):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login already")
    role = await role_repository.get_by_name(UserRoleName.player.value)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Roles not seeded"
        )
    user = User(
        login=data.login,
        first_name=data.first_name,
        last_name=data.last_name,
        nickname=data.nickname,
        password_hash=hash_password(data.password),
        is_active=True,
        role_id=role.id,
    )

    session.add(user)
    await session.flush()

    token_response, jti_hash, refresh_expires_at = _issue_token_pair(user)
    session.add(
        RefreshSession(
            user_id=user.id,
            jti_hash=jti_hash,
            expires_at=refresh_expires_at,
            revoked_at=None,
            replaced_by_jti_hash=None,
        )
    )

    await session.commit()
    return token_response


@router.post("/login", response_model=TokenResponse, summary="Вход")
@limiter.limit("60/minute")
async def login(
    request: Request,
    data: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    user_repository = UserRepository(session)
    user = await user_repository.get_by_login(data.login)
    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token_response, jti_hash, refresh_expires_at = _issue_token_pair(user)
    session.add(
        RefreshSession(
            user_id=user.id,
            jti_hash=jti_hash,
            expires_at=refresh_expires_at,
            revoked_at=None,
            replaced_by_jti_hash=None,
        )
    )
    await session.commit()
    return token_response


@router.post("/refresh", response_model=TokenResponse, summary="Обновить токены")
@limiter.limit("30/minute")
async def refresh_tokens(
    request: Request,
    body: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    payload = safe_decode_token(body.refresh_token)
    if not payload or payload.get("typ") != JWT_TYP_REFRESH or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    jti = payload.get("jti")
    if not isinstance(jti, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    try:
        user_id = int(payload["sub"])
    except TypeError, ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from None

    user_repository = UserRepository(session)
    user = await user_repository.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    refresh_repo = RefreshSessionRepository(session)
    current = await refresh_repo.get_active_by_jti_hash(refresh_jti_hash(jti))
    if not current:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked",
        )

    token_response, new_jti_hash, new_refresh_expires_at = _issue_token_pair(user)
    now = datetime.now(UTC)
    current.revoked_at = now
    current.replaced_by_jti_hash = new_jti_hash
    session.add(
        RefreshSession(
            user_id=user.id,
            jti_hash=new_jti_hash,
            expires_at=new_refresh_expires_at,
            revoked_at=None,
            replaced_by_jti_hash=None,
        )
    )

    await session.commit()
    return token_response


@router.post("/logout", summary="Выход")
async def logout(
    body: LogoutRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, bool]:
    payload = safe_decode_token(body.refresh_token)
    if not payload or payload.get("typ") != JWT_TYP_REFRESH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    jti = payload.get("jti")
    if not isinstance(jti, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    refresh_repo = RefreshSessionRepository(session)
    row = await refresh_repo.get_active_by_jti_hash(refresh_jti_hash(jti))
    if not row or row.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or already revoked",
        )

    row.revoked_at = datetime.now(UTC)
    await session.commit()
    return {"ok": True}


@router.get(
    "/me",
    response_model=UserRead,
    summary="Текущий пользователь",
    description="Возвращает данные авторизованного пользователя.",
)
async def me(user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    return _to_user_read(user)
