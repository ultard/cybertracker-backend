from collections.abc import Iterable
from typing import Any

from app.models import Payment
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository):
    model = Payment

    async def get_by_id(self, id_value: int, *, loads: Iterable[Any] = ()) -> Payment | None:
        return await super().get_by_id(
            id_value,
            loads=[Payment.participant, Payment.tournament, *loads],
        )

    async def list_page(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        tournament_id: int | None = None,
        participant_id: int | None = None,
        status: str | None = None,
    ) -> tuple[list[Payment], int]:
        filters = []
        if tournament_id is not None:
            filters.append(Payment.tournament_id == tournament_id)
        if participant_id is not None:
            filters.append(Payment.participant_id == participant_id)
        if status:
            filters.append(Payment.status == status)
        return await self._list_page(
            filters=filters,
            order_by=Payment.paid_at.desc(),
            loads=[Payment.participant],
            skip=skip,
            limit=limit,
        )
