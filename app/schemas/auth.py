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
