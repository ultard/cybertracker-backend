from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import TournamentStatus, TournamentType


class TournamentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255, description="Название")
    discipline_id: int = Field(description="ID дисциплины")
    tournament_type: TournamentType = TournamentType.offline
    start_at: datetime
    end_at: datetime
    prize_pool: Decimal = Field(ge=0)
    max_participants: int = Field(ge=1, le=100000)
    status: TournamentStatus = TournamentStatus.draft

    @model_validator(mode="after")
    def end_after_start(self) -> TournamentCreate:
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        return self


class TournamentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    discipline_id: int | None = None
    tournament_type: TournamentType | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    prize_pool: Decimal | None = Field(default=None, ge=0)
    max_participants: int | None = Field(default=None, ge=1, le=100000)
    status: TournamentStatus | None = None


class TournamentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    discipline_id: int
    discipline_name: str | None = None
    tournament_type: str
    start_at: datetime
    end_at: datetime
    prize_pool: Decimal
    max_participants: int
    status: str
    created_by_user_id: int | None = None
    created_at: datetime | None = None
