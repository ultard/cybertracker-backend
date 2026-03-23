from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ParticipantLevelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    min_points: int = Field(ge=0)
    sort_order: int = 0


class ParticipantLevelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    min_points: int
    sort_order: int


class ParticipantCreate(BaseModel):
    user_id: int | None = None
    level_id: int | None = None
    first_name: str = Field(min_length=1, max_length=128)
    last_name: str = Field(min_length=1, max_length=128)
    patronymic: str | None = Field(default=None, max_length=128)
    nickname: str = Field(min_length=1, max_length=128)
    birth_date: date | None = None
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    status: str = "active"
    notes: str | None = None


class ParticipantUpdate(BaseModel):
    level_id: int | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=128)
    last_name: str | None = Field(default=None, min_length=1, max_length=128)
    patronymic: str | None = Field(default=None, max_length=128)
    nickname: str | None = Field(default=None, min_length=1, max_length=128)
    birth_date: date | None = None
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    status: str | None = None
    notes: str | None = None


class ParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    level_id: int | None
    first_name: str
    last_name: str
    patronymic: str | None
    nickname: str
    birth_date: date | None
    phone: str | None
    email: str | None
    registered_at: datetime | None
    status: str
    notes: str | None
