from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RegistrationStatus


class RegistrationCreate(BaseModel):
    participant_id: int = Field(description="ID участника")
    tournament_id: int = Field(description="ID турнира")
    status: RegistrationStatus = RegistrationStatus.pending
    comment: str | None = None


class RegistrationUpdate(BaseModel):
    status: RegistrationStatus | None = None
    comment: str | None = None


class RegistrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    participant_id: int
    tournament_id: int
    registered_at: datetime | None
    status: str
    comment: str | None
