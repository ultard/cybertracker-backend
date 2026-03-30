from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_service import write_audit
from app.core.security import hash_password
from app.deps import get_db, require_roles
from app.models import User
from app.models.enums import UserRoleName
from app.repositories import RoleRepository, UserRepository
from app.schemas.common import Page
from app.schemas.role import RoleRead
from app.schemas.user import UserCreate, UserRead, UserUpdate

users_router = APIRouter()
roles_router = APIRouter()

AdminUser = Annotated[User, Depends(require_roles(UserRoleName.admin))]
Staff = Annotated[
    User,
    Depends(require_roles(UserRoleName.admin, UserRoleName.organizer, UserRoleName.manager)),
]


def _read_user(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        login=user.login,
        nickname=user.nickname,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        role_id=user.role_id,
    )


@users_router.get("", response_model=Page[UserRead], summary="Список пользователей")
async def list_users(
    _: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    login: str | None = None,
    role_id: int | None = None,
    is_active: bool | None = None,
) -> Page[UserRead]:
    user_repository = UserRepository(session)
    rows, total = await user_repository.list_users(
        skip=skip, limit=limit, login_filter=login, role_id=role_id, is_active=is_active
    )
    return Page(
        items=[_read_user(user) for user in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@users_router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать пользователя",
    description="Логин и role_id обязательны.",
)
async def create_user(
    _: AdminUser,
    data: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    user_repository = UserRepository(session)
    role_repository = RoleRepository(session)

    if await user_repository.get_by_login(data.login):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login exists")

    if not await role_repository.get_by_id(data.role_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role_id")

    user = User(
        login=data.login,
        password_hash=hash_password(data.password),
        is_active=data.is_active,
        role_id=data.role_id,
        nickname=data.nickname,
        first_name=data.first_name or "",
        last_name=data.last_name or "",
        phone=data.phone,
        email=data.email,
    )
    session.add(user)
    await session.flush()
    await write_audit(session, user_id=_.id, action="user.create", entity="User", entity_id=user.id)
    await session.commit()
    user = await user_repository.get_by_id(user.id)
    assert user
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
    role_repository = RoleRepository(session)
    found_user = await user_repository.get_by_id(user_id)
    if not found_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if (
        data.login
        and data.login != found_user.login
        and await user_repository.get_by_login(data.login)
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login exists")

    if data.role_id is not None and not await role_repository.get_by_id(data.role_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role_id")

    if data.login is not None:
        found_user.login = data.login

    if data.password is not None:
        found_user.password_hash = hash_password(data.password)

    if data.role_id is not None:
        found_user.role_id = data.role_id

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


@roles_router.get("", response_model=list[RoleRead], summary="Список ролей")
async def list_roles(
    _: Staff,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[RoleRead]:
    role_repository = RoleRepository(session)
    roles = await role_repository.list_all()
    return [RoleRead.model_validate(role) for role in roles]
