from pydantic import BaseModel, ConfigDict, Field


class BaseUser(BaseModel):
    login: str
    nickname: str | None

    first_name: str | None
    last_name: str | None

    role_id: int


class UserCreate(BaseUser):
    password: str = Field(min_length=6, max_length=128, description="Пароль")
    phone: str | None = Field(min_length=6, max_length=32, description="Номер телефона")
    email: str | None = Field(min_length=6, max_length=255, description="Почта")
    is_active: bool = True


class UserUpdate(BaseUser):
    login: str | None = Field(default=None, min_length=3, max_length=128)
    password: str | None = Field(default=None, min_length=6, max_length=128, description="Пароль")
    is_active: bool | None = None


class UserRead(BaseUser):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
