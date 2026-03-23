from collections.abc import Iterable
from typing import Any

from sqlalchemy import select

from app.models import Participant, ParticipantLevel
from app.repositories.base import BaseRepository


class ParticipantLevelRepository(BaseRepository):
    model = ParticipantLevel

    async def list_all(self) -> list[ParticipantLevel]:
        return await self._list_all(order_by=ParticipantLevel.sort_order)


class ParticipantRepository(BaseRepository):
    model = Participant

    async def get_by_id(self, id_value: int, *, loads: Iterable[Any] = ()) -> Participant | None:
        return await super().get_by_id(
            id_value, loads=[Participant.level, Participant.user, *loads]
        )

    async def get_by_user_id(self, user_id: int) -> Participant | None:
        result = await self.session.execute(
            select(Participant).where(Participant.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_page(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        nickname: str | None = None,
        email: str | None = None,
    ) -> tuple[list[Participant], int]:
        filters = []
        if nickname:
            filters.append(Participant.nickname.ilike(f"%{nickname}%"))
        if email:
            filters.append(Participant.email.ilike(f"%{email}%"))
        return await self._list_page(
            filters=filters,
            order_by=Participant.id,
            loads=[Participant.level],
            skip=skip,
            limit=limit,
        )
