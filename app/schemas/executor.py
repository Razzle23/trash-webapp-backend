from datetime import datetime
from pydantic import BaseModel, Field


class ExecutorHouseSet(BaseModel):
    house_id: int


class ExecutorOrderCard(BaseModel):
    id: int
    public_number: int
    status: str
    scheduled_at: datetime
    entrance: str
    floor: str
    apartment: str
    comment: str | None
    bags: int
    price: int
    payment: str
    created_at: datetime


class ExecutorInboxResponse(BaseModel):
    house_id: int
    assigned_created: list[ExecutorOrderCard]
    my_active: list[ExecutorOrderCard]


class ExecutorAcceptResponse(BaseModel):
    id: int
    status: str