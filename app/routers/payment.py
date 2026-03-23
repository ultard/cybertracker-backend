"""Платежи."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_service import write_audit
from app.deps import get_db, require_roles
from app.models import Payment, User
from app.models.enums import UserRoleName
from app.repositories import ParticipantRepository, PaymentRepository, RegistrationRepository
from app.schemas.common import Page
from app.schemas.payment import PaymentCreate, PaymentRead, PaymentUpdate

router = APIRouter()
Staff = Annotated[User, Depends(require_roles(UserRoleName.admin, UserRoleName.organizer))]


def _to_payment_read(payment: Payment) -> PaymentRead:
    return PaymentRead.model_validate(payment)


@router.get(
    "",
    response_model=Page[PaymentRead],
    summary="Список платежей",
    description="Фильтры: tournament_id, participant_id, status. admin/organizer.",
)
async def list_payments(
    _: Staff,
    session: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    tournament_id: int | None = None,
    participant_id: int | None = None,
    status: str | None = None,
) -> Page[PaymentRead]:
    payment_repository = PaymentRepository(session)
    rows, total = await payment_repository.list_page(
        skip=skip,
        limit=limit,
        tournament_id=tournament_id,
        participant_id=participant_id,
        status=status,
    )
    return Page(
        items=[_to_payment_read(payment) for payment in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать платёж",
)
async def create_payment(
    user: Staff,
    data: PaymentCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentRead:
    participant_repository = ParticipantRepository(session)
    if not await participant_repository.get_by_id(data.participant_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="participant not found")
    if data.registration_id is not None:
        registration_repository = RegistrationRepository(session)
        if not await registration_repository.get_by_id(data.registration_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="registration not found"
            )
    payment = Payment(
        participant_id=data.participant_id,
        tournament_id=data.tournament_id,
        registration_id=data.registration_id,
        employee_id=data.employee_id,
        amount=data.amount,
        method=data.method.value,
        status=data.status.value,
        comment=data.comment,
    )
    session.add(payment)
    await session.flush()
    await write_audit(
        session,
        user_id=user.id,
        action="payment.create",
        entity="Payment",
        entity_id=payment.id,
    )
    await session.commit()
    payment_repository = PaymentRepository(session)
    created_payment = await payment_repository.get_by_id(payment.id)
    assert created_payment
    return _to_payment_read(created_payment)


@router.get(
    "/{payment_id}",
    response_model=PaymentRead,
    summary="Платёж по ID",
)
async def get_payment(
    _: Staff,
    payment_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentRead:
    payment_repository = PaymentRepository(session)
    payment = await payment_repository.get_by_id(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _to_payment_read(payment)


@router.patch(
    "/{payment_id}",
    response_model=PaymentRead,
    summary="Обновить платёж",
)
async def update_payment(
    user: Staff,
    payment_id: int,
    data: PaymentUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentRead:
    payment_repository = PaymentRepository(session)
    payment = await payment_repository.get_by_id(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is None:
            continue
        if key == "method":
            payment.method = value.value if hasattr(value, "value") else str(value)
        elif key == "status":
            payment.status = value.value if hasattr(value, "value") else str(value)
        else:
            setattr(payment, key, value)
    await write_audit(
        session,
        user_id=user.id,
        action="payment.update",
        entity="Payment",
        entity_id=payment.id,
    )
    await session.commit()
    payment_repository = PaymentRepository(session)
    updated_payment = await payment_repository.get_by_id(payment_id)
    assert updated_payment
    return _to_payment_read(updated_payment)
