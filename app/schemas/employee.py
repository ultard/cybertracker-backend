from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class EmployeeCreate(BaseModel):
    user_id: int | None = None
    first_name: str = Field(min_length=1, max_length=128)
    last_name: str = Field(min_length=1, max_length=128)
    patronymic: str | None = Field(default=None, max_length=128)
    position: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    hired_at: date
    fired_at: date | None = None
    is_judge: bool = False
    notes: str | None = None


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=128)
    last_name: str | None = Field(default=None, min_length=1, max_length=128)
    patronymic: str | None = Field(default=None, max_length=128)
    position: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    hired_at: date | None = None
    fired_at: date | None = None
    is_judge: bool | None = None
    notes: str | None = None


class EmployeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    first_name: str
    last_name: str
    patronymic: str | None
    position: str
    phone: str | None
    email: str | None
    hired_at: date
    fired_at: date | None
    is_judge: bool
    notes: str | None
