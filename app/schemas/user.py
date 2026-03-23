from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    login: str = Field(min_length=3, max_length=128, description="Уникальный логин")
    password: str = Field(min_length=6, max_length=128, description="Пароль")
    role_id: int = Field(description="ID роли")
    is_active: bool = True


class UserUpdate(BaseModel):
    login: str | None = Field(default=None, min_length=3, max_length=128)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    role_id: int | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    is_active: bool
    role_id: int
    role_name: str | None = None
