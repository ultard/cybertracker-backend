from collections.abc import Iterable
from typing import Any, ClassVar, Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import ColumnElement


class ModelWithId(Protocol):
    """Protocol для моделей с первичным ключом id."""

    id: Any


class BaseRepository:
    model: ClassVar[type[ModelWithId]]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(
        self,
        id_value: int,
        *,
        loads: Iterable[Any] = (),
    ) -> Any | None:
        """Выборка по первичному ключу id с опциональной подгрузкой связей."""
        q = select(self.model).where(self.model.id == id_value)
        for load in loads:
            q = q.options(selectinload(load))
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def _list_page(
        self,
        *,
        filters: Iterable[ColumnElement[bool]] = (),
        order_by: Any = None,
        loads: Iterable[Any] = (),
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Any], int]:
        """Пагинированный список с фильтрами, сортировкой и подгрузкой связей."""
        flist = list(filters)
        count_q = select(func.count()).select_from(self.model)
        if flist:
            count_q = count_q.where(*flist)
        total = int((await self.session.execute(count_q)).scalar_one())

        q = select(self.model)
        for load in loads:
            q = q.options(selectinload(load))
        if flist:
            q = q.where(*flist)
        if order_by is not None:
            q = q.order_by(order_by)
        q = q.offset(skip).limit(limit)
        rows = (await self.session.execute(q)).scalars().all()
        return list(rows), total

    async def _list_all(self, *, order_by: Any = None) -> list[Any]:
        """Список всех записей без пагинации."""
        q = select(self.model)
        if order_by is not None:
            q = q.order_by(order_by)
        rows = (await self.session.execute(q)).scalars().all()
        return list(rows)
