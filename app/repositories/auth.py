from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Role, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    model = User

    async def get_by_id(self, id_value: int, *, loads: Iterable[Any] = ()) -> User | None:
        return await super().get_by_id(id_value, loads=[User.role, *loads])

    async def get_by_login(self, login: str) -> User | None:
        result = await self.session.execute(
            select(User).options(selectinload(User.role)).where(User.login == login)
        )
        return result.scalar_one_or_none()

    async def list_users(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        login_filter: str | None = None,
        role_id: int | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[User], int]:
        filters = []
        if login_filter:
            filters.append(User.login.ilike(f"%{login_filter}%"))
        if role_id is not None:
            filters.append(User.role_id == role_id)
        if is_active is not None:
            filters.append(User.is_active == is_active)
        return await self._list_page(
            filters=filters,
            order_by=User.id,
            loads=[User.role],
            skip=skip,
            limit=limit,
        )


class RoleRepository(BaseRepository):
    model = Role

    async def get_by_id(self, id_value: int, *, loads: Iterable[Any] = ()) -> Role | None:
        return await super().get_by_id(id_value, loads=loads)

    async def get_by_name(self, name: str) -> Role | None:
        result = await self.session.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Role]:
        return await self._list_all(order_by=Role.id)
