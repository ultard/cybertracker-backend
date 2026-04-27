from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_service import write_audit
from app.deps import get_current_user, get_db, require_roles
from app.models import User
from app.models.enums import UserRole
from app.repositories import UserRepository
from app.schemas.common import Page
from app.schemas.user import ProfileUpdate, UserRead, UserUpdate

users_router = APIRouter()

AdminUser = Annotated[User, Depends(require_roles(UserRole.admin))]


def _read_user(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        login=user.login,
        nickname=user.nickname,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        role=UserRole(user.role),
    )


@users_router.get("", response_model=Page[UserRead], summary="Список пользователей")
async def list_users(
    _: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    login: str | None = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> Page[UserRead]:
    user_repository = UserRepository(session)
    rows, total = await user_repository.list_users(
        skip=skip,
        limit=limit,
        login_filter=login,
        role=role.value if role is not None else None,
        is_active=is_active,
    )
    return Page(
        items=[_read_user(user) for user in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@users_router.get("/me", response_model=UserRead, summary="Текущий пользователь")
async def get_me(user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    return _read_user(user)


@users_router.patch("/me", response_model=UserRead, summary="Обновить свой профиль")
async def update_my_profile(
    user: Annotated[User, Depends(get_current_user)],
    data: ProfileUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    if data.nickname is not None:
        user.nickname = data.nickname
    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name
    await session.commit()
    await session.refresh(user)
    return _read_user(user)


@users_router.get("/{user_id}", response_model=UserRead, summary="Пользователь по ID")
async def get_user(
    _: AdminUser,
    user_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    user_repository = UserRepository(session)
    found_user = await user_repository.get_by_id(user_id)

    if not found_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return _read_user(found_user)


@users_router.patch("/{user_id}", response_model=UserRead, summary="Обновить пользователя")
async def update_user(
    _: AdminUser,
    user_id: int,
    data: UserUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    user_repository = UserRepository(session)
    found_user = await user_repository.get_by_id(user_id)
    if not found_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if (
        data.login
        and data.login != found_user.login
        and await user_repository.get_by_login(data.login)
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login exists")

    if data.login is not None:
        found_user.login = data.login

    if data.nickname is not None:
        found_user.nickname = data.nickname

    if data.first_name is not None:
        found_user.first_name = data.first_name

    if data.last_name is not None:
        found_user.last_name = data.last_name

    if data.role is not None:
        found_user.role = data.role.value

    if data.is_active is not None:
        found_user.is_active = data.is_active

    await write_audit(
        session, user_id=_.id, action="user.update", entity="User", entity_id=found_user.id
    )
    await session.commit()
    found_user = await user_repository.get_by_id(user_id)
    assert found_user
    return _read_user(found_user)


@users_router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить пользователя",
)
async def delete_user(
    _: AdminUser,
    user_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    user_repository = UserRepository(session)
    found_user = await user_repository.get_by_id(user_id)

    if not found_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await write_audit(
        session, user_id=_.id, action="user.delete", entity="User", entity_id=found_user.id
    )
    await session.delete(found_user)
    await session.commit()


__all__ = ["users_router"]
