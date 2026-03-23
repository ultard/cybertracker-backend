from collections.abc import Iterable
from typing import Any

from sqlalchemy import func, select

from app.models import (
    AttendanceLog,
    AttendancePrediction,
    MatchResult,
    Registration,
    Tournament,
)
from app.repositories.base import BaseRepository


class TournamentRepository(BaseRepository):
    model = Tournament

    async def get_by_id(self, id_value: int, *, loads: Iterable[Any] = ()) -> Tournament | None:
        return await super().get_by_id(id_value, loads=[Tournament.discipline, *loads])

    async def list_page(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        discipline_id: int | None = None,
        status: str | None = None,
        name: str | None = None,
    ) -> tuple[list[Tournament], int]:
        filters = []
        if discipline_id is not None:
            filters.append(Tournament.discipline_id == discipline_id)
        if status:
            filters.append(Tournament.status == status)
        if name:
            filters.append(Tournament.name.ilike(f"%{name}%"))
        return await self._list_page(
            filters=filters,
            order_by=Tournament.start_at.desc(),
            loads=[Tournament.discipline],
            skip=skip,
            limit=limit,
        )


class RegistrationRepository(BaseRepository):
    model = Registration

    async def get_by_id(self, id_value: int, *, loads: Iterable[Any] = ()) -> Registration | None:
        return await super().get_by_id(
            id_value,
            loads=[Registration.participant, Registration.tournament, *loads],
        )

    async def get_by_participant_tournament(
        self, participant_id: int, tournament_id: int
    ) -> Registration | None:
        result = await self.session.execute(
            select(Registration).where(
                Registration.participant_id == participant_id,
                Registration.tournament_id == tournament_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_for_tournament(self, tournament_id: int, status: str | None = None) -> int:
        query = (
            select(func.count())
            .select_from(Registration)
            .where(Registration.tournament_id == tournament_id)
        )
        if status:
            query = query.where(Registration.status == status)
        return int((await self.session.execute(query)).scalar_one())

    async def list_for_tournament(
        self, tournament_id: int, *, skip: int = 0, limit: int = 50
    ) -> tuple[list[Registration], int]:
        filters = [Registration.tournament_id == tournament_id]
        return await self._list_page(
            filters=filters,
            order_by=Registration.registered_at.desc(),
            loads=[Registration.participant],
            skip=skip,
            limit=limit,
        )


class MatchRepository(BaseRepository):
    model = MatchResult

    async def get_by_id(self, id_value: int, *, loads: Iterable[Any] = ()) -> MatchResult | None:
        return await super().get_by_id(id_value, loads=[MatchResult.tournament, *loads])

    async def list_for_tournament(
        self, tournament_id: int, *, skip: int = 0, limit: int = 50
    ) -> tuple[list[MatchResult], int]:
        filters = [MatchResult.tournament_id == tournament_id]
        return await self._list_page(
            filters=filters,
            order_by=MatchResult.played_at.desc(),
            skip=skip,
            limit=limit,
        )


class PredictionRepository(BaseRepository):
    model = AttendancePrediction

    async def get_by_id(
        self, id_value: int, *, loads: Iterable[Any] = ()
    ) -> AttendancePrediction | None:
        return await super().get_by_id(id_value, loads=[AttendancePrediction.tournament, *loads])

    async def list_for_tournament(
        self, tournament_id: int, *, skip: int = 0, limit: int = 20
    ) -> tuple[list[AttendancePrediction], int]:
        filters = [AttendancePrediction.tournament_id == tournament_id]
        return await self._list_page(
            filters=filters,
            order_by=AttendancePrediction.predicted_at.desc(),
            skip=skip,
            limit=limit,
        )


class AttendanceRepository(BaseRepository):
    model = AttendanceLog

    async def create(self, log: AttendanceLog) -> AttendanceLog:
        self.session.add(log)
        await self.session.flush()
        return log
