from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.attendance import predict_attendance, recommendations
from app.config import get_settings
from app.core.audit_service import write_audit
from app.deps import get_current_user, get_db, require_roles
from app.models import AttendanceLog, AttendancePrediction, QRSession, User
from app.models.enums import UserRole
from app.repositories import (
    ParticipantRepository,
    QRRepository,
    TournamentRepository,
)
from app.schemas.prediction import PredictResponse
from app.schemas.qr import QRGenerateResponse, QRValidateRequest, QRValidateResponse

audit_router = APIRouter()
qr_router = APIRouter()
predict_router = APIRouter()

settings = get_settings()


class AuditRead(BaseModel):
    """Запись журнала аудита."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    action: str
    entity: str
    entity_id: int | None
    created_at: object | None
    changes: dict | None


@audit_router.get("", response_model=list[AuditRead], summary="Журнал аудита")
async def list_audit(
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
    session: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    entity: str | None = None,
    user_id: int | None = None,
) -> list[AuditRead]:
    from app.repositories import AuditRepository

    audit_repository = AuditRepository(session)
    rows, _total = await audit_repository.list_page(
        skip=skip, limit=limit, entity=entity, user_id=user_id
    )
    return [AuditRead.model_validate(audit_row) for audit_row in rows]


@qr_router.post(
    "/generate",
    response_model=QRGenerateResponse,
    summary="Сгенерировать QR-токен",
    description=(
        "Токен для прохода."
    ),
)
async def generate_qr(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    tournament_id: int = Query(..., description="Турнир, в котором вы участвуете"),
) -> QRGenerateResponse:
    participant_repository = ParticipantRepository(session)
    participant = await participant_repository.get_by_user_tournament(user.id, tournament_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    now = datetime.now(UTC)
    expires = now + timedelta(seconds=settings.qr_token_ttl_seconds)
    token = uuid4().hex + uuid4().hex
    qr_session = QRSession(
        participant_id=participant.id, token=token, expires_at=expires, used=False
    )
    session.add(qr_session)
    await session.flush()
    await write_audit(
        session,
        user_id=user.id,
        action="qr.generate",
        entity="QRSession",
        entity_id=qr_session.id,
    )
    await session.commit()
    return QRGenerateResponse(token=token, expires_at=expires)


@qr_router.post(
    "/validate",
    response_model=QRValidateResponse,
    summary="Проверить QR и отметить посещение",
    description="Создаёт запись AttendanceLog.",
)
async def validate_qr(
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.organizer))],
    body: QRValidateRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> QRValidateResponse:
    qr_repository = QRRepository(session)
    participant_repository = ParticipantRepository(session)
    qr_session = await qr_repository.get_by_token(body.token)
    now = datetime.now(UTC)
    if not qr_session or qr_session.used or qr_session.expires_at <= now:
        return QRValidateResponse(ok=False, message="Invalid or expired token")
    participant = await participant_repository.get_by_id(qr_session.participant_id)
    if not participant:
        return QRValidateResponse(ok=False, message="Participant missing")
    qr_session.used = True
    attendance_log = AttendanceLog(
        participant_id=participant.id,
        qr_session_id=qr_session.id,
    )
    session.add(attendance_log)
    await session.flush()
    await write_audit(
        session,
        user_id=user.id,
        action="attendance.checkin",
        entity="AttendanceLog",
        entity_id=attendance_log.id,
    )
    await session.commit()
    return QRValidateResponse(ok=True, participant_id=participant.id, message="Checked in")


PredictUser = Annotated[
    User,
    Depends(require_roles(UserRole.admin, UserRole.organizer, UserRole.manager)),
]


@predict_router.post(
    "/tournament/{tournament_id}",
    response_model=PredictResponse,
    summary="Прогноз посещаемости",
    description=(
        "Прогноз по турниру"
    ),
)
async def predict(
    user: PredictUser,
    tournament_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PredictResponse:
    tournament_repository = TournamentRepository(session)
    tournament = await tournament_repository.get_by_id(tournament_id)

    if not tournament:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")

    participant_repository = ParticipantRepository(session)
    registered_count = await participant_repository.count_for_tournament(tournament_id)
    pred, metrics = predict_attendance(
        discipline_name=tournament.discipline.name,
        tournament_type=tournament.tournament_type,
        event_datetime=tournament.start_at,
        prize_pool=float(tournament.prize_pool),
        registered_count=registered_count,
    )
    recs = recommendations(
        predicted=pred,
        max_participants=tournament.max_participants,
        prize_pool=float(tournament.prize_pool),
    )
    attendance_prediction = AttendancePrediction(
        tournament_id=tournament_id,
        predicted_attendance=pred,
        actual_attendance=None,
        mae=Decimal(str(metrics["mae"])) if metrics.get("mae") is not None else None,
        rmse=Decimal(str(metrics["rmse"])) if metrics.get("rmse") is not None else None,
        r2=Decimal(str(metrics["r2"])) if metrics.get("r2") is not None else None,
    )
    session.add(attendance_prediction)
    await session.flush()
    await write_audit(
        session,
        user_id=user.id,
        action="predict.run",
        entity="AttendancePrediction",
        entity_id=attendance_prediction.id,
    )
    await session.commit()
    return PredictResponse(
        predicted_attendance=pred,
        model_metrics=metrics or None,
        recommendations=recs,
    )

