from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole


class BaseUser(BaseModel):
    login: str
    nickname: str | None

    first_name: str | None
    last_name: str | None

    role: UserRole


class UserCreate(BaseUser):
    password: str = Field(min_length=6, max_length=128, description="Пароль")
    phone: str | None = Field(min_length=6, max_length=32, description="Номер телефона")
    email: str | None = Field(min_length=6, max_length=255, description="Почта")
    is_active: bool = True


class UserUpdate(BaseModel):
    """Частичное обновление пользователя (админ)."""

    login: str | None = Field(default=None, min_length=3, max_length=128)
    nickname: str | None = Field(default=None, max_length=128)
    first_name: str | None = Field(default=None, min_length=1, max_length=128)
    last_name: str | None = Field(default=None, min_length=1, max_length=128)
    role: UserRole | None = None
    is_active: bool | None = None


class ProfileUpdate(BaseModel):
    """Профиль текущего пользователя (без смены логина и роли)."""

    nickname: str | None = Field(default=None, max_length=128)
    first_name: str | None = Field(default=None, min_length=1, max_length=128)
    last_name: str | None = Field(default=None, min_length=1, max_length=128)


class UserRead(BaseUser):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
