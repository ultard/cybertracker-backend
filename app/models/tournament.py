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
from app.models.enums import ParticipantRole, ParticipantStatus, TournamentStatus, TournamentType

_json_type = JSON().with_variant(JSONB, "postgresql")

if TYPE_CHECKING:
    from app.models.auth import User
    from app.models.discipline import Discipline
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
    participants: Mapped[list[Participant]] = relationship(back_populates="tournament")
    match_results: Mapped[list[MatchResult]] = relationship(back_populates="tournament")
    predictions: Mapped[list[AttendancePrediction]] = relationship(back_populates="tournament")


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("user_id", "tournament_id", name="uq_participant_user_tournament"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), index=True
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[str] = mapped_column(
        String(32), default=ParticipantStatus.pending.value, nullable=False, index=True
    )
    participant_role: Mapped[str] = mapped_column(
        String(32), default=ParticipantRole.player.value, nullable=False, index=True
    )

    user: Mapped[User] = relationship(lazy="joined")
    tournament: Mapped[Tournament] = relationship(back_populates="participants")
    qr_sessions: Mapped[list[QRSession]] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan",
    )
    attendance_logs: Mapped[list[AttendanceLog]] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan",
    )


class MatchResult(Base):
    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), index=True
    )
    played_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    winner_participant_id: Mapped[int | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL"), nullable=True
    )
    participant_a_id: Mapped[int | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL"), nullable=True
    )
    participant_b_id: Mapped[int | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL"), nullable=True
    )
    score: Mapped[str | None] = mapped_column(String(64), nullable=True)
    comment: Mapped[str | None] = mapped_column(String(512), nullable=True)

    tournament: Mapped[Tournament] = relationship(back_populates="match_results")
    winner_participant: Mapped[Participant | None] = relationship(
        "Participant", foreign_keys=[winner_participant_id]
    )
    participant_a: Mapped[Participant | None] = relationship(
        "Participant", foreign_keys=[participant_a_id]
    )
    participant_b: Mapped[Participant | None] = relationship(
        "Participant", foreign_keys=[participant_b_id]
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
