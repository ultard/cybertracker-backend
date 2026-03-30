from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RegistrationStatus


class RegistrationCreate(BaseModel):
    participant_id: int | None = Field(default=None)
    tournament_id: int = Field(description="ID турнира")
    status: RegistrationStatus = RegistrationStatus.pending


class RegistrationUpdate(BaseModel):
    status: RegistrationStatus | None = None


class RegistrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    participant_id: int
    tournament_id: int
    registered_at: datetime | None
    status: str
