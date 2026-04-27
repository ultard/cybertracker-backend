from collections.abc import Iterable
from typing import Any

from sqlalchemy import func, or_, select

from app.models import (
    AttendanceLog,
    AttendancePrediction,
    MatchResult,
    Participant,
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
        visible_statuses: tuple[str, ...] | None = None,
    ) -> tuple[list[Tournament], int]:
        filters = []
        if discipline_id is not None:
            filters.append(Tournament.discipline_id == discipline_id)
        if status:
            filters.append(Tournament.status == status)
        if visible_statuses is not None:
            filters.append(Tournament.status.in_(visible_statuses))
        if name:
            filters.append(Tournament.name.ilike(f"%{name}%"))
        return await self._list_page(
            filters=filters,
            order_by=Tournament.start_at.desc(),
            loads=[Tournament.discipline],
            skip=skip,
            limit=limit,
        )


class ParticipantRepository(BaseRepository):
    model = Participant

    async def get_by_id(self, id_value: int, *, loads: Iterable[Any] = ()) -> Participant | None:
        return await super().get_by_id(
            id_value,
            loads=[Participant.user, Participant.tournament, *loads],
        )

    async def get_by_user_tournament(self, user_id: int, tournament_id: int) -> Participant | None:
        result = await self.session.execute(
            select(Participant).where(
                Participant.user_id == user_id,
                Participant.tournament_id == tournament_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_for_tournament(
        self,
        tournament_id: int,
        status: str | None = None,
        participant_role: str | None = None,
        exclude_participant_id: int | None = None,
    ) -> int:
        query = (
            select(func.count())
            .select_from(Participant)
            .where(Participant.tournament_id == tournament_id)
        )
        if status:
            query = query.where(Participant.status == status)
        if participant_role:
            query = query.where(Participant.participant_role == participant_role)
        if exclude_participant_id is not None:
            query = query.where(Participant.id != exclude_participant_id)
        return int((await self.session.execute(query)).scalar_one())

    async def list_for_tournament(
        self,
        tournament_id: int,
        *,
        skip: int = 0,
        limit: int = 50,
        user_id: int | None = None,
        status: str | None = None,
        exclude_statuses: tuple[str, ...] | None = None,
        viewer_user_id: int | None = None,
    ) -> tuple[list[Participant], int]:
        filters = [Participant.tournament_id == tournament_id]
        if user_id is not None:
            filters.append(Participant.user_id == user_id)
        if status is not None:
            filters.append(Participant.status == status)
        if exclude_statuses:
            if viewer_user_id is not None:
                filters.append(
                    or_(
                        Participant.status.notin_(exclude_statuses),
                        Participant.user_id == viewer_user_id,
                    )
                )
            else:
                filters.append(Participant.status.notin_(exclude_statuses))
        return await self._list_page(
            filters=filters,
            order_by=Participant.registered_at.desc(),
            loads=[Participant.user],
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
