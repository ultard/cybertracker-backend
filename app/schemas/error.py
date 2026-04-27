from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorInfo(BaseModel):
    code: str = Field(description="Короткий машинный код ошибки")
    message: str = Field(description="Человекочитаемое сообщение")
    details: Any | None = Field(default=None, description="Опциональные детали (например ошибки валидации)")
    request_id: str | None = Field(default=None, description="ID запроса (если передан клиентом)")


class ErrorEnvelope(BaseModel):
    error: ErrorInfo

