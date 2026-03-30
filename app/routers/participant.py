from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_service import write_audit
from app.deps import get_current_user, get_db, require_roles
from app.models import Participant, User
from app.models.enums import UserRoleName
from app.repositories import ParticipantRepository, UserRepository
from app.schemas.common import Page
from app.schemas.participant import (
    ParticipantCreate,
    ParticipantRead,
    ParticipantUpdate,
)

router = APIRouter()
AdminOrg = Annotated[
    User,
    Depends(require_roles(UserRoleName.admin, UserRoleName.organizer)),
]


def _to_participant_read(participant: Participant) -> ParticipantRead:
    return ParticipantRead.model_validate(participant)


@router.get(
    "",
    response_model=Page[ParticipantRead],
    summary="Список участников",
    description="Пагинация. admin/organizer.",
)
async def list_participants(
    _: AdminOrg,
    session: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
) -> Page[ParticipantRead]:
    participant_repository = ParticipantRepository(session)
    rows, total = await participant_repository.list_page(skip=skip, limit=limit)
    return Page(
        items=[_to_participant_read(participant) for participant in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=ParticipantRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать участника",
    description="admin/organizer. user_id опционален.",
)
async def create_participant(
    _: AdminOrg,
    data: ParticipantCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ParticipantRead:
    participant_repository = ParticipantRepository(session)
    user_repository = UserRepository(session)
    if data.user_id is not None and not await user_repository.get_by_id(data.user_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id not found")
    participant = Participant(
        user_id=data.user_id,
        status=data.status,
    )
    session.add(participant)
    await session.flush()
    await write_audit(
        session,
        user_id=_.id,
        action="participant.create",
        entity="Participant",
        entity_id=participant.id,
    )
    await session.commit()
    created_participant = await participant_repository.get_by_id(participant.id)
    assert created_participant
    return _to_participant_read(created_participant)


@router.get(
    "/me",
    response_model=ParticipantRead,
    summary="Мой профиль участника",
    description="Профиль участника для текущего пользователя.",
)
async def my_participant(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ParticipantRead:
    participant_repository = ParticipantRepository(session)
    participant = await participant_repository.get_by_user_id(user.id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No participant profile")
    return _to_participant_read(participant)


@router.get(
    "/{participant_id}",
    response_model=ParticipantRead,
    summary="Участник по ID",
)
async def get_participant(
    user: Annotated[User, Depends(get_current_user)],
    participant_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ParticipantRead:
    participant_repository = ParticipantRepository(session)
    participant = await participant_repository.get_by_id(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role.name not in (
        UserRoleName.admin.value,
        UserRoleName.organizer.value,
        UserRoleName.judge.value,
        UserRoleName.manager.value,
    ):
        my_participant = await participant_repository.get_by_user_id(user.id)
        if not my_participant or my_participant.id != participant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return _to_participant_read(participant)


@router.patch(
    "/{participant_id}",
    response_model=ParticipantRead,
    summary="Обновить участника",
)
async def update_participant(
    user: Annotated[User, Depends(get_current_user)],
    participant_id: int,
    data: ParticipantUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ParticipantRead:
    participant_repository = ParticipantRepository(session)
    participant = await participant_repository.get_by_id(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role.name not in (UserRoleName.admin.value, UserRoleName.organizer.value):
        my_participant = await participant_repository.get_by_user_id(user.id)
        if not my_participant or my_participant.id != participant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(participant, key, value)
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
    return _to_participant_read(updated_participant)


@router.delete(
    "/{participant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить участника",
    description="Только admin.",
)
async def delete_participant(
    _: Annotated[User, Depends(require_roles(UserRoleName.admin))],
    participant_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    participant_repository = ParticipantRepository(session)
    participant = await participant_repository.get_by_id(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await write_audit(
        session,
        user_id=_.id,
        action="participant.delete",
        entity="Participant",
        entity_id=participant.id,
    )
    await session.delete(participant)
    await session.commit()
