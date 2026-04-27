from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_service import write_audit
from app.deps import get_current_user, get_current_user_optional, get_db, require_roles
from app.models import MatchResult, Participant, Tournament, User
from app.models.enums import (
    ParticipantRole,
    ParticipantStatus,
    TournamentStatus,
    UserRole,
)
from app.repositories import (
    DisciplineRepository,
    MatchRepository,
    ParticipantRepository,
    TournamentRepository,
)
from app.schemas.common import Page
from app.schemas.match import MatchCreate, MatchRead, MatchUpdate
from app.schemas.participant import ParticipantRead, ParticipantRegister, ParticipantUpdate
from app.schemas.tournament import TournamentCreate, TournamentRead, TournamentUpdate

tournaments_router = APIRouter()

_TOURNAMENT_STAFF_ROLES = frozenset(
    {
        UserRole.admin.value,
        UserRole.organizer.value,
        UserRole.judge.value,
        UserRole.manager.value,
    }
)

_PUBLIC_TOURNAMENT_STATUSES = (
    TournamentStatus.recruiting.value,
    TournamentStatus.in_progress.value,
    TournamentStatus.completed.value,
    TournamentStatus.cancelled.value,
)


def _user_sees_non_public_tournaments(user: User | None) -> bool:
    return user is not None and user.role in _TOURNAMENT_STAFF_ROLES


def _ensure_tournament_readable(user: User | None, tournament: Tournament | None) -> Tournament:
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if _user_sees_non_public_tournaments(user) or tournament.status in _PUBLIC_TOURNAMENT_STATUSES:
        return tournament
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


Org = Annotated[
    User,
    Depends(require_roles(UserRole.admin, UserRole.organizer)),
]


async def _validate_match_participants(
    participant_repository: ParticipantRepository,
    tournament_id: int,
    *,
    winner_id: int | None,
    a_id: int | None,
    b_id: int | None,
) -> None:
    async def _one(pid: int | None) -> None:
        if pid is None:
            return
        p = await participant_repository.get_by_id(pid)
        if not p:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="participant not found",
            )
        if p.tournament_id != tournament_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="participant does not belong to this tournament",
            )
        if p.participant_role != ParticipantRole.player.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="only players (not spectators) can be assigned to a match",
            )

    await _one(winner_id)
    await _one(a_id)
    await _one(b_id)
    in_match = {x for x in (a_id, b_id) if x is not None}
    if winner_id is not None and in_match and winner_id not in in_match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="winner must be participant_a or participant_b",
        )


def _read_tournament(tournament: Tournament) -> TournamentRead:
    discipline_name = (
        tournament.discipline.name if getattr(tournament, "discipline", None) else None
    )
    return TournamentRead(
        id=tournament.id,
        name=tournament.name,
        discipline_id=tournament.discipline_id,
        discipline_name=discipline_name,
        tournament_type=tournament.tournament_type,
        start_at=tournament.start_at,
        end_at=tournament.end_at,
        prize_pool=tournament.prize_pool,
        max_participants=tournament.max_participants,
        status=tournament.status,
        created_at=tournament.created_at,
        created_by_user_id=tournament.created_by_user_id,
    )


@tournaments_router.get(
    "",
    response_model=Page[TournamentRead],
    summary="Список турниров"
)
async def list_tournaments(
    user: Annotated[User | None, Depends(get_current_user_optional)],
    session: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    discipline_id: int | None = None,
    status: TournamentStatus | None = None,
    name: str | None = None,
) -> Page[TournamentRead]:
    tournament_repository = TournamentRepository(session)
    visible_statuses = (
        None
        if _user_sees_non_public_tournaments(user)
        else _PUBLIC_TOURNAMENT_STATUSES
    )
    rows, total = await tournament_repository.list_page(
        skip=skip,
        limit=limit,
        discipline_id=discipline_id,
        status=status.value if status is not None else None,
        name=name,
        visible_statuses=visible_statuses,
    )
    return Page(
        items=[_read_tournament(tournament) for tournament in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@tournaments_router.post(
    "", 
    response_model=TournamentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать турнир"
)
async def create_tournament(
    user: Org,
    data: TournamentCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TournamentRead:
    discipline_repository = DisciplineRepository(session)
    if not await discipline_repository.get_by_id(data.discipline_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="discipline_id not found"
        )
    tournament = Tournament(
        name=data.name,
        discipline_id=data.discipline_id,
        tournament_type=data.tournament_type.value,
        start_at=data.start_at,
        end_at=data.end_at,
        prize_pool=data.prize_pool,
        max_participants=data.max_participants,
        status=data.status.value,
        created_by_user_id=user.id,
    )
    session.add(tournament)
    await session.flush()
    await write_audit(
        session,
        user_id=user.id,
        action="tournament.create",
        entity="Tournament",
        entity_id=tournament.id,
    )
    await session.commit()
    tournament_repository = TournamentRepository(session)
    created_tournament = await tournament_repository.get_by_id(tournament.id)
    assert created_tournament
    return _read_tournament(created_tournament)


@tournaments_router.get(
    "/{tournament_id}",
    response_model=TournamentRead,
    summary="Турнир по ID",
)
async def get_tournament(
    user: Annotated[User | None, Depends(get_current_user_optional)],
    tournament_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TournamentRead:
    tournament_repository = TournamentRepository(session)
    tournament = await tournament_repository.get_by_id(tournament_id)
    tournament = _ensure_tournament_readable(user, tournament)
    return _read_tournament(tournament)


@tournaments_router.patch(
    "/{tournament_id}",
    response_model=TournamentRead,
    summary="Обновить турнир",
)
async def update_tournament(
    user: Org,
    tournament_id: int,
    data: TournamentUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TournamentRead:
    tournament_repository = TournamentRepository(session)
    discipline_repository = DisciplineRepository(session)
    tournament = await tournament_repository.get_by_id(tournament_id)
    if not tournament:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if data.discipline_id is not None and not await discipline_repository.get_by_id(
        data.discipline_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="discipline_id not found"
        )
    if data.name is not None:
        tournament.name = data.name
    if data.discipline_id is not None:
        tournament.discipline_id = data.discipline_id
    if data.tournament_type is not None:
        tournament.tournament_type = data.tournament_type.value
    if data.start_at is not None:
        tournament.start_at = data.start_at
    if data.end_at is not None:
        tournament.end_at = data.end_at
    if data.prize_pool is not None:
        tournament.prize_pool = data.prize_pool
    if data.max_participants is not None:
        tournament.max_participants = data.max_participants
    if data.status is not None:
        tournament.status = data.status.value
    if tournament.end_at <= tournament.start_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid dates")
    await write_audit(
        session,
        user_id=user.id,
        action="tournament.update",
        entity="Tournament",
        entity_id=tournament.id,
    )
    await session.commit()
    updated_tournament = await tournament_repository.get_by_id(tournament_id)
    assert updated_tournament
    return _read_tournament(updated_tournament)


@tournaments_router.post(
    "/{tournament_id}/activate",
    response_model=TournamentRead,
    summary="Активировать турнир",
    description="Переводит турнир в статус recruiting.",
)
async def activate_tournament(
    user: Org,
    tournament_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TournamentRead:
    tournament_repository = TournamentRepository(session)
    tournament = await tournament_repository.get_by_id(tournament_id)
    if not tournament:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    tournament.status = TournamentStatus.recruiting.value
    await write_audit(
        session,
        user_id=user.id,
        action="tournament.activate",
        entity="Tournament",
        entity_id=tournament.id,
    )
    await session.commit()
    activated_tournament = await tournament_repository.get_by_id(tournament_id)
    assert activated_tournament
    return _read_tournament(activated_tournament)


# --- Participants router ---

participants_router = APIRouter()

ParticipantStaff = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.admin,
            UserRole.organizer,
            UserRole.manager,
            UserRole.judge,
        )
    ),
]


def _read_participant(participant: Participant) -> ParticipantRead:
    nickname = participant.user.nickname if getattr(participant, "user", None) else None
    return ParticipantRead(
        id=participant.id,
        user_id=participant.user_id,
        tournament_id=participant.tournament_id,
        registered_at=participant.registered_at,
        status=participant.status,
        participant_role=ParticipantRole(participant.participant_role),
        nickname=nickname,
    )


@participants_router.get(
    "",
    response_model=Page[ParticipantRead],
    summary="Участники турнира",
    description=(
        "Фильтр по tournament_id. Персонал — полный список; остальные — все участники турнира, "
        "кроме чужих заявок в статусе pending (своя заявка с тем же статусом для авторизованного "
        "пользователя показывается)."
    ),
)
async def list_participants(
    user: Annotated[User | None, Depends(get_current_user_optional)],
    session: Annotated[AsyncSession, Depends(get_db)],
    tournament_id: int = Query(..., description="Filter by tournament"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Page[ParticipantRead]:
    tournament_repository = TournamentRepository(session)
    tournament = await tournament_repository.get_by_id(tournament_id)
    _ensure_tournament_readable(user, tournament)
    participant_repository = ParticipantRepository(session)
    if user and user.role in (
        UserRole.admin.value,
        UserRole.organizer.value,
        UserRole.judge.value,
        UserRole.manager.value,
    ):
        rows, total = await participant_repository.list_for_tournament(
            tournament_id, skip=skip, limit=limit
        )
    else:
        rows, total = await participant_repository.list_for_tournament(
            tournament_id,
            skip=skip,
            limit=limit,
            exclude_statuses=(ParticipantStatus.pending.value,),
            viewer_user_id=user.id if user else None,
        )
    return Page(
        items=[_read_participant(participant) for participant in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@participants_router.get(
    "/{participant_id}",
    response_model=ParticipantRead,
    summary="Участник турнира по ID",
)
async def get_participant(
    user: Annotated[User | None, Depends(get_current_user_optional)],
    participant_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ParticipantRead:
    participant_repository = ParticipantRepository(session)
    participant = await participant_repository.get_by_id(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    _ensure_tournament_readable(user, participant.tournament)
    if user is None:
        if participant.status != ParticipantStatus.confirmed.value:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    elif (
        user.role
        not in (
            UserRole.admin.value,
            UserRole.organizer.value,
            UserRole.judge.value,
            UserRole.manager.value,
        )
        and participant.user_id != user.id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return _read_participant(participant)


@participants_router.post(
    "/register",
    response_model=ParticipantRead,
    status_code=status.HTTP_201_CREATED,
    summary="Записаться на турнир",
    description="Текущий пользователь оформляет участие в турнире."
)
async def register_for_tournament(
    user: Annotated[User, Depends(get_current_user)],
    data: ParticipantRegister,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ParticipantRead:
    participant_repository = ParticipantRepository(session)
    tournament_repository = TournamentRepository(session)
    tournament = await tournament_repository.get_by_id(data.tournament_id)
    tournament = _ensure_tournament_readable(user, tournament)

    if tournament.status != TournamentStatus.recruiting.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tournament not open")

    if await participant_repository.get_by_user_tournament(user.id, data.tournament_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already registered")

    participant = Participant(
        user_id=user.id,
        tournament_id=data.tournament_id,
        status=ParticipantStatus.pending.value,
        participant_role=data.participant_role.value,
    )
    session.add(participant)
    await session.flush()
    await write_audit(
        session,
        user_id=user.id,
        action="participant.register",
        entity="Participant",
        entity_id=participant.id,
    )
    await session.commit()
    created_participant = await participant_repository.get_by_id(participant.id)
    assert created_participant
    return _read_participant(created_participant)


@participants_router.patch(
    "/{participant_id}",
    response_model=ParticipantRead,
    summary="Обновить участника турнира",
    description="Обновляет статус участия в турнире.",
)
async def update_participant(
    user: ParticipantStaff,
    participant_id: int,
    data: ParticipantUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ParticipantRead:
    participant_repository = ParticipantRepository(session)
    participant = await participant_repository.get_by_id(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    new_status = data.status.value if data.status is not None else participant.status
    new_role = (
        data.participant_role.value
        if data.participant_role is not None
        else participant.participant_role
    )
    if new_role == ParticipantRole.player.value and new_status == ParticipantStatus.confirmed.value:
        tournament_repository = TournamentRepository(session)
        t = await tournament_repository.get_by_id(participant.tournament_id)
        assert t
        count = await participant_repository.count_for_tournament(
            participant.tournament_id,
            status=ParticipantStatus.confirmed.value,
            participant_role=ParticipantRole.player.value,
            exclude_participant_id=participant.id,
        )
        if count >= t.max_participants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Tournament is full"
            )
    if data.status is not None:
        participant.status = data.status.value
    if data.participant_role is not None:
        participant.participant_role = data.participant_role.value
    await write_audit(
        session,
        user_id=user.id,
        action="participant.update",
        entity="Participant",
        entity_id=participant.id,
    )
    await session.commit()
    updated_participant = await participant_repository.get_by_id(participant_id)
    assert updated_participant
    return _read_participant(updated_participant)


@participants_router.delete(
    "/{participant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить участника турнира",
)
async def delete_participant(
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.organizer))],
    participant_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    participant_repository = ParticipantRepository(session)
    participant = await participant_repository.get_by_id(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    entity_id = participant.id
    await write_audit(
        session,
        user_id=user.id,
        action="participant.delete",
        entity="Participant",
        entity_id=entity_id,
    )
    await session.delete(participant)
    await session.commit()


# --- Matches router ---

matches_router = APIRouter()
JudgeOrg = Annotated[
    User,
    Depends(require_roles(UserRole.admin, UserRole.organizer, UserRole.judge)),
]


def _read_match(match: MatchResult) -> MatchRead:
    return MatchRead.model_validate(match)


@matches_router.get(
    "",
    response_model=Page[MatchRead],
    summary="Список матчей"
)
async def list_matches(
    user: Annotated[User | None, Depends(get_current_user_optional)],
    session: Annotated[AsyncSession, Depends(get_db)],
    tournament_id: int = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Page[MatchRead]:
    tournament_repository = TournamentRepository(session)
    tournament = await tournament_repository.get_by_id(tournament_id)
    _ensure_tournament_readable(user, tournament)
    match_repository = MatchRepository(session)
    rows, total = await match_repository.list_for_tournament(tournament_id, skip=skip, limit=limit)
    return Page(
        items=[_read_match(match) for match in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@matches_router.post(
    "",
    response_model=MatchRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать матч",
)
async def create_match(
    user: JudgeOrg,
    data: MatchCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MatchRead:
    tournament_repository = TournamentRepository(session)
    participant_repository = ParticipantRepository(session)
    if not await tournament_repository.get_by_id(data.tournament_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tournament not found")
    await _validate_match_participants(
        participant_repository,
        data.tournament_id,
        winner_id=data.winner_participant_id,
        a_id=data.participant_a_id,
        b_id=data.participant_b_id,
    )
    played_at = data.played_at or datetime.now(UTC)
    match = MatchResult(
        tournament_id=data.tournament_id,
        played_at=played_at,
        winner_participant_id=data.winner_participant_id,
        participant_a_id=data.participant_a_id,
        participant_b_id=data.participant_b_id,
        score=data.score,
        comment=data.comment,
    )
    session.add(match)
    await session.flush()
    await write_audit(
        session,
        user_id=user.id,
        action="match.create",
        entity="MatchResult",
        entity_id=match.id,
    )
    await session.commit()
    match_repository = MatchRepository(session)
    created_match = await match_repository.get_by_id(match.id)
    assert created_match
    return _read_match(created_match)


@matches_router.get(
    "/{match_id}",
    response_model=MatchRead,
    summary="Матч по ID",
)
async def get_match(
    user: Annotated[User | None, Depends(get_current_user_optional)],
    match_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MatchRead:
    match_repository = MatchRepository(session)
    match = await match_repository.get_by_id(match_id)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    _ensure_tournament_readable(user, match.tournament)
    return _read_match(match)


@matches_router.patch(
    "/{match_id}",
    response_model=MatchRead,
    summary="Обновить матч",
)
async def update_match(
    user: JudgeOrg,
    match_id: int,
    data: MatchUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MatchRead:
    match_repository = MatchRepository(session)
    participant_repository = ParticipantRepository(session)
    match = await match_repository.get_by_id(match_id)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(match, key, value)
    await _validate_match_participants(
        participant_repository,
        match.tournament_id,
        winner_id=match.winner_participant_id,
        a_id=match.participant_a_id,
        b_id=match.participant_b_id,
    )
    await write_audit(
        session,
        user_id=user.id,
        action="match.update",
        entity="MatchResult",
        entity_id=match.id,
    )
    await session.commit()
    updated_match = await match_repository.get_by_id(match_id)
    assert updated_match
    return _read_match(updated_match)

__all__ = ["tournaments_router", "participants_router", "matches_router"]
