from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.limiter import limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.deps import get_current_user, get_db
from app.models import Participant, User
from app.models.enums import UserRoleName
from app.repositories import RoleRepository, UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.user import UserRead

router = APIRouter()
settings = get_settings()


def _to_user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        login=user.login,
        is_active=user.is_active,
        role_id=user.role_id,
        role_name=user.role.name if user.role else None,
    )


@router.post(
    "/register",
    response_model=UserRead,
    summary="Регистрация",
    description="Создаёт учётную запись с ролью игрок и профиль участника.",
)
async def register(
    data: RegisterRequest, session: Annotated[AsyncSession, Depends(get_db)]
) -> UserRead:
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
        password_hash=hash_password(data.password),
        is_active=True,
        role_id=role.id,
    )
    session.add(user)
    await session.flush()
    participant = Participant(
        user_id=user.id,
        first_name=data.first_name,
        last_name=data.last_name,
        nickname=data.nickname,
        email=None,
        status="active",
    )
    session.add(participant)
    await session.commit()
    await session.refresh(user)
    user = (await user_repository.get_by_id(user.id)) or user
    return _to_user_read(user)


@router.post(
    "/login",
    summary="Вход",
    description="Проверяет логин/пароль, устанавливает JWT в cookie.",
)
@limiter.limit("60/minute")
async def login(
    request: Request,
    data: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    user_repository = UserRepository(session)
    user = await user_repository.get_by_login(data.login)
    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(str(user.id), extra={"role": user.role.name})
    resp = JSONResponse(content=_to_user_read(user).model_dump(mode="json"))
    resp.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return resp


@router.post(
    "/logout",
    summary="Выход",
    description="Удаляет JWT cookie. Требует предварительной авторизации.",
)
async def logout() -> JSONResponse:
    resp = JSONResponse(content={"ok": True})
    resp.delete_cookie(settings.cookie_name, path="/")
    return resp


@router.get(
    "/me",
    response_model=UserRead,
    summary="Текущий пользователь",
    description="Возвращает данные авторизованного пользователя.",
)
async def me(user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    return _to_user_read(user)
