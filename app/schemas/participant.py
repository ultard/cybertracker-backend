from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ParticipantRole, ParticipantStatus


class ParticipantRegister(BaseModel):
    """Тело запроса: текущий пользователь записывает себя на турнир."""

    tournament_id: int = Field(description="ID турнира")
    participant_role: ParticipantRole = ParticipantRole.player


class ParticipantUpdate(BaseModel):
    status: ParticipantStatus | None = None
    participant_role: ParticipantRole | None = None


class ParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    tournament_id: int
    registered_at: datetime | None
    status: str
    participant_role: ParticipantRole
    nickname: str | None = None

