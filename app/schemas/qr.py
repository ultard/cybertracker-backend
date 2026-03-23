from datetime import datetime

from pydantic import BaseModel, Field


class QRGenerateResponse(BaseModel):
    token: str = Field(description="Токен для отображения в QR")
    expires_at: datetime = Field(description="Время истечения")


class QRValidateRequest(BaseModel):
    token: str = Field(min_length=8, max_length=256, description="Токен из QR")


class QRValidateResponse(BaseModel):
    ok: bool
    registration_id: int | None = None
    message: str
