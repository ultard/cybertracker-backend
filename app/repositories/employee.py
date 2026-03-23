from collections.abc import Iterable
from typing import Any

from app.models import Employee
from app.repositories.base import BaseRepository


class EmployeeRepository(BaseRepository):
    model = Employee

    async def get_by_id(self, id_value: int, *, loads: Iterable[Any] = ()) -> Employee | None:
        return await super().get_by_id(id_value, loads=[Employee.user, *loads])

    async def list_page(
        self, *, skip: int = 0, limit: int = 20, position: str | None = None
    ) -> tuple[list[Employee], int]:
        filters = []
        if position:
            filters.append(Employee.position.ilike(f"%{position}%"))
        return await self._list_page(
            filters=filters,
            order_by=Employee.id,
            skip=skip,
            limit=limit,
        )
