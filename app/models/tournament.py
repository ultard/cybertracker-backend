from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base
from app.models.enums import RegistrationStatus, TournamentStatus, TournamentType

_json_type = JSON().with_variant(JSONB, "postgresql")

if TYPE_CHECKING:
    from app.models.discipline import Discipline
    from app.models.participant import Participant
    from app.models.system import AttendanceLog, QRSession


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    discipline_id: Mapped[int] = mapped_column(
        ForeignKey("disciplines.id", ondelete="RESTRICT"), index=True
    )
    tournament_type: Mapped[str] = mapped_column(
        String(32), default=TournamentType.offline.value, nullable=False, index=True
    )

    prize_pool: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    max_participants: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=TournamentStatus.draft.value, nullable=False, index=True
    )

    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    discipline: Mapped[Discipline] = relationship(back_populates="tournaments")
    registrations: Mapped[list[Registration]] = relationship(back_populates="tournament")
    match_results: Mapped[list[MatchResult]] = relationship(back_populates="tournament")
    predictions: Mapped[list[AttendancePrediction]] = relationship(back_populates="tournament")


class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = (
        UniqueConstraint("participant_id", "tournament_id", name="uq_reg_participant_tournament"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), index=True
    )
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), index=True
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[str] = mapped_column(
        String(32), default=RegistrationStatus.pending.value, nullable=False, index=True
    )

    participant: Mapped[Participant] = relationship(back_populates="registrations")
    tournament: Mapped[Tournament] = relationship(back_populates="registrations")
    qr_sessions: Mapped[list[QRSession]] = relationship(back_populates="registration")
    attendance_logs: Mapped[list[AttendanceLog]] = relationship(back_populates="registration")


class MatchResult(Base):
    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), index=True
    )
    played_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    winner_registration_id: Mapped[int | None] = mapped_column(
        ForeignKey("registrations.id", ondelete="SET NULL"), nullable=True
    )
    participant_a_registration_id: Mapped[int | None] = mapped_column(
        ForeignKey("registrations.id", ondelete="SET NULL"), nullable=True
    )
    participant_b_registration_id: Mapped[int | None] = mapped_column(
        ForeignKey("registrations.id", ondelete="SET NULL"), nullable=True
    )
    score: Mapped[str | None] = mapped_column(String(64), nullable=True)

    tournament: Mapped[Tournament] = relationship(back_populates="match_results")
    winner_registration: Mapped[Registration | None] = relationship(
        "Registration", foreign_keys=[winner_registration_id]
    )
    participant_a: Mapped[Registration | None] = relationship(
        "Registration", foreign_keys=[participant_a_registration_id]
    )
    participant_b: Mapped[Registration | None] = relationship(
        "Registration", foreign_keys=[participant_b_registration_id]
    )


class AttendancePrediction(Base):
    __tablename__ = "attendance_predictions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), index=True
    )
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    predicted_attendance: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_attendance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mae: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    rmse: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    r2: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)

    tournament: Mapped[Tournament] = relationship(back_populates="predictions")
