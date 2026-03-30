from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PredictRequest(BaseModel):
    tournament_id: int | None = None


class PredictResponse(BaseModel):
    predicted_attendance: int = Field(description="Прогнозируемое число посетителей")
    model_metrics: dict[str, float | None] | None = Field(
        default=None,
        description="Метрики качества модели (если посчитаны; при чистом инференсе обычно пусто)",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Краткие рекомендации по результатам прогноза",
    )


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
