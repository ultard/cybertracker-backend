from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.auth import User
    from app.models.tournament import Participant

_json_type = JSON().with_variant(JSONB, "postgresql")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    changes: Mapped[dict[str, Any] | None] = mapped_column(_json_type, nullable=True)

    user: Mapped[User | None] = relationship(back_populates="audit_logs")


class QRSession(Base):
    __tablename__ = "qr_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), index=True
    )
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    participant: Mapped[Participant] = relationship(back_populates="qr_sessions")
    attendance_logs: Mapped[list[AttendanceLog]] = relationship(back_populates="qr_session")


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), index=True
    )
    qr_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("qr_sessions.id", ondelete="SET NULL"), nullable=True
    )
    passed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    participant: Mapped[Participant] = relationship(back_populates="attendance_logs")
    qr_session: Mapped[QRSession | None] = relationship(back_populates="attendance_logs")
