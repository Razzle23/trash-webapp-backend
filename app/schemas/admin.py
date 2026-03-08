from datetime import datetime
from pydantic import BaseModel


class LiveStatsOut(BaseModel):
    house_id: int
    unaccepted: int
    accepted: int


class AdminExecutorOut(BaseModel):
    id: int
    name: str
    house_id: int | None
    online: bool
    active_accepted: int


class AdminOrderOut(BaseModel):
    id: int
    public_number: int
    status: str
    house_id: int
    entrance: str
    floor: str
    apartment: str
    comment: str | None
    bags: int
    price: int
    payment: str
    scheduled_at: datetime
    customer_id: int
    executor_id: int | None
    created_at: datetime
    assigned_executor_id: int | None
    assigned_at: datetime | None


class CancelReq(BaseModel):
    reason: str | None = None