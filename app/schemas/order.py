from datetime import datetime
from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    time_slot: str = Field(pattern="^(morning|evening)$")  # morning|evening
    bags: int = Field(ge=1, le=3)
    payment: str  # cash|transfer|sbp


class OrderOut(BaseModel):
    id: int
    public_number: int
    status: str
    scheduled_at: datetime
    price: int
    payment: str
    created_at: datetime