from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    login: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=4, max_length=128)


class RegisterRequest(BaseModel):
    login: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=6, max_length=128)
    first_name: str = Field(min_length=1, max_length=128)
    last_name: str = Field(min_length=1, max_length=128)
    nickname: str = Field(min_length=1, max_length=128)


class TokenPayload(BaseModel):
    sub: str
    role: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="TTL access_token в секундах")
    refresh_expires_in: int = Field(description="TTL refresh_token в секундах")


class MeResponse(BaseModel):
    id: int
    login: str
    nickname: str | None
    first_name: str | None
    last_name: str | None
    is_active: bool
    role: str
