from pydantic import BaseModel, ConfigDict, Field


class DisciplineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128, description="Название")
    description: str | None = None
    min_age: int = Field(default=0, ge=0, le=100, description="Минимальный возраст")


class DisciplineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    min_age: int | None = Field(default=None, ge=0, le=100)


class DisciplineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    min_age: int
