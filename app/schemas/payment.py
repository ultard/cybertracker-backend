from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentMethod, PaymentStatus


class PaymentCreate(BaseModel):
    participant_id: int = Field(description="ID участника")
    tournament_id: int | None = None
    registration_id: int | None = None
    employee_id: int | None = None
    amount: Decimal = Field(ge=0)
    method: PaymentMethod = PaymentMethod.online
    status: PaymentStatus = PaymentStatus.pending
    comment: str | None = None


class PaymentUpdate(BaseModel):
    tournament_id: int | None = None
    registration_id: int | None = None
    employee_id: int | None = None
    amount: Decimal | None = Field(default=None, ge=0)
    method: PaymentMethod | None = None
    status: PaymentStatus | None = None
    comment: str | None = None


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    participant_id: int
    tournament_id: int | None
    registration_id: int | None
    employee_id: int | None
    paid_at: datetime | None
    amount: Decimal
    method: str
    status: str
    comment: str | None
