from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MatchCreate(BaseModel):
    tournament_id: int = Field(description="ID турнира")
    played_at: datetime | None = None
    winner_registration_id: int | None = None
    participant_a_registration_id: int | None = None
    participant_b_registration_id: int | None = None
    score: str | None = Field(default=None, max_length=64)
    comment: str | None = None


class MatchUpdate(BaseModel):
    played_at: datetime | None = None
    winner_registration_id: int | None = None
    participant_a_registration_id: int | None = None
    participant_b_registration_id: int | None = None
    score: str | None = Field(default=None, max_length=64)
    comment: str | None = None


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tournament_id: int
    played_at: datetime | None
    winner_registration_id: int | None
    participant_a_registration_id: int | None
    participant_b_registration_id: int | None
    score: str | None
    comment: str | None
