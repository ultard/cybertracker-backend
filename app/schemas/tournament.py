from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import TournamentStatus, TournamentType

TOURNAMENT_SCHEDULE_MAX_YEARS = 2


def _add_years(dt: datetime, years: int) -> datetime:
    try:
        return dt.replace(year=dt.year + years)
    except ValueError:
        return dt.replace(month=2, day=28, year=dt.year + years)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def tournament_schedule_bounds() -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    return now, _add_years(now, TOURNAMENT_SCHEDULE_MAX_YEARS)


def ensure_tournament_datetime_in_bounds(dt: datetime) -> None:
    dt_utc = _as_utc(dt)
    min_dt, max_dt = tournament_schedule_bounds()
    if dt_utc < min_dt:
        raise ValueError("Дата проведения не может быть в прошлом")
    if dt_utc > max_dt:
        raise ValueError(
            f"Дата проведения не может быть более чем на {TOURNAMENT_SCHEDULE_MAX_YEARS} года вперёд"
        )


class TournamentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255, description="Название")
    discipline_id: int = Field(description="ID дисциплины")
    tournament_type: TournamentType = TournamentType.offline
    start_at: datetime
    end_at: datetime
    prize_pool: Decimal = Field(ge=0)
    max_participants: int = Field(ge=1, le=100000)
    status: TournamentStatus = TournamentStatus.draft

    @field_validator("start_at", "end_at")
    @classmethod
    def validate_schedule_datetime(cls, v: datetime) -> datetime:
        ensure_tournament_datetime_in_bounds(v)
        return v

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

    @field_validator("start_at", "end_at")
    @classmethod
    def validate_schedule_datetime(cls, v: datetime | None) -> datetime | None:
        if v is not None:
            ensure_tournament_datetime_in_bounds(v)
        return v


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
    created_at: datetime | None = None
    created_by_user_id: int | None = None
