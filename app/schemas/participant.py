from pydantic import BaseModel, ConfigDict, Field


class ParticipantCreate(BaseModel):
    user_id: int | None = None
    status: str = Field(default="active", max_length=32)


class ParticipantUpdate(BaseModel):
    status: str | None = Field(default=None, max_length=32)


class ParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    status: str
