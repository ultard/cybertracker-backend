from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_service import write_audit
from app.deps import get_current_user, get_db, require_roles
from app.models import MatchResult, Participant, Registration, Tournament, User
from app.models.enums import RegistrationStatus, TournamentStatus, UserRoleName
from app.repositories import (
    DisciplineRepository,
    MatchRepository,
    ParticipantRepository,
    RegistrationRepository,
    TournamentRepository,
)
from app.schemas.common import Page
from app.schemas.match import MatchCreate, MatchRead, MatchUpdate
from app.schemas.registration import RegistrationCreate, RegistrationRead, RegistrationUpdate
from app.schemas.tournament import TournamentCreate, TournamentRead, TournamentUpdate

tournaments_router = APIRouter()

Org = Annotated[
    User,
    Depends(require_roles(UserRoleName.admin, UserRoleName.organizer)),
]

Reader = Annotated[
    User,
    Depends(
        require_roles(
            UserRoleName.admin,
            UserRoleName.organizer,
            UserRoleName.judge,
            UserRoleName.manager,
            UserRoleName.player,
            UserRoleName.spectator,
        )
    ),
]


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
        created_by_user_id=tournament.created_by_user_id,
        created_at=tournament.created_at,
    )


@tournaments_router.get(
    "",
    response_model=Page[TournamentRead],
    summary="Список турниров",
    description="Пагинация. Фильтры: discipline_id, status. Все авторизованные.",
)
async def list_tournaments(
    _: Reader,
    session: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    discipline_id: int | None = None,
    status: str | None = None,
    name: str | None = None,
) -> Page[TournamentRead]:
    tournament_repository = TournamentRepository(session)
    rows, total = await tournament_repository.list_page(
        skip=skip, limit=limit, discipline_id=discipline_id, status=status, name=name
    )
    return Page(
        items=[_read_tournament(tournament) for tournament in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@tournaments_router.post(
    "", response_model=TournamentRead, status_code=status.HTTP_201_CREATED, summary="Создать турнир"
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
    _: Reader,
    tournament_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TournamentRead:
    tournament_repository = TournamentRepository(session)
    tournament = await tournament_repository.get_by_id(tournament_id)
    if not tournament:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
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
    description="Переводит турнир в статус active.",
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
    tournament.status = TournamentStatus.active.value
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


# --- Registrations router ---

registrations_router = APIRouter()


def _read_registration(registration: Registration) -> RegistrationRead:
    return RegistrationRead.model_validate(registration)


@registrations_router.get(
    "",
    response_model=Page[RegistrationRead],
    summary="Регистрации на турнир",
    description="Фильтр по tournament_id. Персонал видит все, игрок — только свои.",
)
async def list_registrations(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    tournament_id: int = Query(..., description="Filter by tournament"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Page[RegistrationRead]:
    registration_repository = RegistrationRepository(session)
    participant_repository = ParticipantRepository(session)
    rows, total = await registration_repository.list_for_tournament(
        tournament_id, skip=skip, limit=limit
    )
    if user.role.name in (
        UserRoleName.admin.value,
        UserRoleName.organizer.value,
        UserRoleName.judge.value,
        UserRoleName.manager.value,
    ):
        return Page(
            items=[_read_registration(registration) for registration in rows],
            total=total,
            skip=skip,
            limit=limit,
        )
    my_participant = await participant_repository.get_by_user_id(user.id)
    if not my_participant:
        return Page(items=[], total=0, skip=skip, limit=limit)
    filtered_rows = [row for row in rows if row.participant_id == my_participant.id]
    return Page(
        items=[_read_registration(registration) for registration in filtered_rows],
        total=len(filtered_rows),
        skip=skip,
        limit=limit,
    )


@registrations_router.get(
    "/{registration_id}",
    response_model=RegistrationRead,
    summary="Регистрация по ID",
)
async def get_registration(
    user: Annotated[User, Depends(get_current_user)],
    registration_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RegistrationRead:
    registration_repository = RegistrationRepository(session)
    participant_repository = ParticipantRepository(session)
    registration = await registration_repository.get_by_id(registration_id)
    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role.name not in (
        UserRoleName.admin.value,
        UserRoleName.organizer.value,
        UserRoleName.judge.value,
        UserRoleName.manager.value,
    ):
        my_participant = await participant_repository.get_by_user_id(user.id)
        if not my_participant or registration.participant_id != my_participant.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return _read_registration(registration)


@registrations_router.post(
    "",
    response_model=RegistrationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрироваться на турнир",
    description="Участник может регистрировать себя. Организатор — любого участника.",
)
async def create_registration(
    user: Annotated[User, Depends(get_current_user)],
    data: RegistrationCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RegistrationRead:
    registration_repository = RegistrationRepository(session)
    participant_repository = ParticipantRepository(session)
    tournament_repository = TournamentRepository(session)
    tournament = await tournament_repository.get_by_id(data.tournament_id)
    if not tournament:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    if tournament.status not in (
        TournamentStatus.active.value,
        TournamentStatus.draft.value,
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tournament not open")
    participant_id = data.participant_id
    if user.role.name in (UserRoleName.player.value, UserRoleName.spectator.value):
        my_participant = await participant_repository.get_by_user_id(user.id)
        if my_participant:
            participant_id = my_participant.id
            if data.participant_id is not None and data.participant_id != participant_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        else:
            participant = Participant(
                user_id=user.id,
                status="active",
            )
            session.add(participant)
            await session.flush()
            participant_id = participant.id
    elif user.role.name not in (UserRoleName.admin.value, UserRoleName.organizer.value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    if participant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="participant_id required"
        )
    participant = await participant_repository.get_by_id(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="participant not found")
    if await registration_repository.get_by_participant_tournament(
        participant_id, data.tournament_id
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already registered")
    count = await registration_repository.count_for_tournament(
        data.tournament_id, status=RegistrationStatus.confirmed.value
    )
    if count >= tournament.max_participants:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tournament is full")
    registration = Registration(
        participant_id=participant_id,
        tournament_id=data.tournament_id,
        status=data.status.value,
    )
    session.add(registration)
    await session.flush()
    await write_audit(
        session,
        user_id=user.id,
        action="registration.create",
        entity="Registration",
        entity_id=registration.id,
    )
    await session.commit()
    created_registration = await registration_repository.get_by_id(registration.id)
    assert created_registration
    return _read_registration(created_registration)


@registrations_router.patch(
    "/{registration_id}",
    response_model=RegistrationRead,
    summary="Обновить регистрацию",
    description="Статус регистрации.",
)
async def update_registration(
    user: Annotated[User, Depends(require_roles(UserRoleName.admin, UserRoleName.organizer))],
    registration_id: int,
    data: RegistrationUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RegistrationRead:
    registration_repository = RegistrationRepository(session)
    registration = await registration_repository.get_by_id(registration_id)
    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if data.status is not None:
        registration.status = data.status.value
    await write_audit(
        session,
        user_id=user.id,
        action="registration.update",
        entity="Registration",
        entity_id=registration.id,
    )
    await session.commit()
    updated_registration = await registration_repository.get_by_id(registration_id)
    assert updated_registration
    return _read_registration(updated_registration)


# --- Matches router ---

matches_router = APIRouter()
JudgeOrg = Annotated[
    User,
    Depends(require_roles(UserRoleName.admin, UserRoleName.organizer, UserRoleName.judge)),
]


def _read_match(match: MatchResult) -> MatchRead:
    return MatchRead.model_validate(match)


@matches_router.get(
    "",
    response_model=Page[MatchRead],
    summary="Список матчей",
    description="Фильтр tournament_id. admin/organizer/judge.",
)
async def list_matches(
    _: JudgeOrg,
    session: Annotated[AsyncSession, Depends(get_db)],
    tournament_id: int = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Page[MatchRead]:
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
    if not await tournament_repository.get_by_id(data.tournament_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tournament not found")
    played_at = data.played_at or datetime.now(UTC)
    match = MatchResult(
        tournament_id=data.tournament_id,
        played_at=played_at,
        winner_registration_id=data.winner_registration_id,
        participant_a_registration_id=data.participant_a_registration_id,
        participant_b_registration_id=data.participant_b_registration_id,
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
    _: JudgeOrg,
    match_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MatchRead:
    match_repository = MatchRepository(session)
    match = await match_repository.get_by_id(match_id)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
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
    match = await match_repository.get_by_id(match_id)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(match, key, value)
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


__all__ = ["tournaments_router", "registrations_router", "matches_router"]
