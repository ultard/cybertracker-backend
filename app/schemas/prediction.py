from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PredictRequest(BaseModel):
    tournament_id: int | None = None
    discipline_id: int = Field(ge=1, description="ID дисциплины")
    tournament_type: str = Field(pattern="^(online|offline)$", description="online или offline")
    event_datetime: datetime
    prize_pool: Decimal = Field(ge=0)
    registered_count: int = Field(ge=0)


class PredictResponse(BaseModel):
    predicted_attendance: int = Field(description="Прогнозируемое число посетителей")
    model_metrics: dict | None = None
    recommendations: list[str] = Field(default_factory=list, description="Рекомендации")


class PredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tournament_id: int
    predicted_at: datetime | None
    predicted_attendance: int
    actual_attendance: int | None
    mae: Decimal | None
    rmse: Decimal | None
    r2: Decimal | None
