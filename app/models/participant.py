from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ParticipantStatus

if TYPE_CHECKING:
    from app.models.auth import User
    from app.models.system import AttendanceLog
    from app.models.tournament import Registration


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True
    )

    status: Mapped[str] = mapped_column(
        String(32), default=ParticipantStatus.active.value, nullable=False
    )

    user: Mapped[User | None] = relationship(back_populates="participant")
    registrations: Mapped[list[Registration]] = relationship(back_populates="participant")
    attendance_logs: Mapped[list[AttendanceLog]] = relationship(back_populates="participant")
