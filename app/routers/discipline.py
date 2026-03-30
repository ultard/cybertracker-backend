from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_service import write_audit
from app.deps import get_db, require_roles
from app.models import Discipline, User
from app.models.enums import UserRoleName
from app.repositories import DisciplineRepository
from app.schemas.common import Page
from app.schemas.discipline import DisciplineCreate, DisciplineRead, DisciplineUpdate

router = APIRouter()
Admin = Annotated[User, Depends(require_roles(UserRoleName.admin))]
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


@router.get(
    "",
    response_model=Page[DisciplineRead],
    summary="Список дисциплин",
    description="Пагинация и фильтр по имени. Все авторизованные.",
)
async def list_disciplines(
    _: Reader,
    session: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    name: str | None = None,
) -> Page[DisciplineRead]:
    discipline_repository = DisciplineRepository(session)
    rows, total = await discipline_repository.list_page(skip=skip, limit=limit, name=name)
    return Page(
        items=[DisciplineRead.model_validate(x) for x in rows], total=total, skip=skip, limit=limit
    )


@router.post(
    "",
    response_model=DisciplineRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать дисциплину",
    description="Название, описание, минимальный возраст. Только admin.",
)
async def create_discipline(
    _: Admin,
    data: DisciplineCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DisciplineRead:
    discipline = Discipline(name=data.name, description=data.description, min_age=data.min_age)
    session.add(discipline)
    await session.flush()
    await write_audit(
        session,
        user_id=_.id,
        action="discipline.create",
        entity="Discipline",
        entity_id=discipline.id,
    )
    await session.commit()
    await session.refresh(discipline)
    return DisciplineRead.model_validate(discipline)


@router.get(
    "/{discipline_id}",
    response_model=DisciplineRead,
    summary="Дисциплина по ID",
)
async def get_discipline(
    _: Reader,
    discipline_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DisciplineRead:
    discipline_repository = DisciplineRepository(session)
    discipline = await discipline_repository.get_by_id(discipline_id)
    if not discipline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return DisciplineRead.model_validate(discipline)


@router.patch(
    "/{discipline_id}",
    response_model=DisciplineRead,
    summary="Обновить дисциплину",
)
async def update_discipline(
    _: Admin,
    discipline_id: int,
    data: DisciplineUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DisciplineRead:
    discipline_repository = DisciplineRepository(session)
    discipline = await discipline_repository.get_by_id(discipline_id)
    if not discipline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if data.name is not None:
        discipline.name = data.name
    if data.description is not None:
        discipline.description = data.description
    if data.min_age is not None:
        discipline.min_age = data.min_age
    await write_audit(
        session,
        user_id=_.id,
        action="discipline.update",
        entity="Discipline",
        entity_id=discipline.id,
    )
    await session.commit()
    await session.refresh(discipline)
    return DisciplineRead.model_validate(discipline)


@router.delete(
    "/{discipline_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить дисциплину",
)
async def delete_discipline(
    _: Admin,
    discipline_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    discipline_repository = DisciplineRepository(session)
    discipline = await discipline_repository.get_by_id(discipline_id)
    if not discipline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await write_audit(
        session,
        user_id=_.id,
        action="discipline.delete",
        entity="Discipline",
        entity_id=discipline.id,
    )
    await session.delete(discipline)
    await session.commit()
