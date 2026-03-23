from collections.abc import Iterable
from typing import Any

from app.models import Discipline
from app.repositories.base import BaseRepository


class DisciplineRepository(BaseRepository):
    model = Discipline

    async def get_by_id(self, id_value: int, *, loads: Iterable[Any] = ()) -> Discipline | None:
        return await super().get_by_id(id_value, loads=loads)

    async def list_page(
        self, *, skip: int = 0, limit: int = 20, name: str | None = None
    ) -> tuple[list[Discipline], int]:
        filters = []
        if name:
            filters.append(Discipline.name.ilike(f"%{name}%"))
        return await self._list_page(
            filters=filters, order_by=Discipline.id, skip=skip, limit=limit
        )
