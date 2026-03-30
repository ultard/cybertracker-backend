from collections.abc import Iterable
from typing import Any

from sqlalchemy import select

from app.models import Participant
from app.repositories.base import BaseRepository


class ParticipantRepository(BaseRepository):
    model = Participant

    async def get_by_id(self, id_value: int, *, loads: Iterable[Any] = ()) -> Participant | None:
        return await super().get_by_id(id_value, loads=[Participant.user, *loads])

    async def get_by_user_id(self, user_id: int) -> Participant | None:
        result = await self.session.execute(
            select(Participant).where(Participant.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_page(self, *, skip: int = 0, limit: int = 20) -> tuple[list[Participant], int]:
        return await self._list_page(
            order_by=Participant.id,
            skip=skip,
            limit=limit,
        )
