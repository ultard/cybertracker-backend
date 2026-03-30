from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PredictRequest(BaseModel):
    tournament_id: int | None = None


class PredictResponse(BaseModel):
    predicted_attendance: int = Field(description="Прогнозируемое число посетителей")


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
