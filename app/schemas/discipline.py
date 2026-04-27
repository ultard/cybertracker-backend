from pydantic import BaseModel, ConfigDict, Field


class DisciplineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128, description="Название")
    description: str | None = None


class DisciplineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None


class DisciplineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
