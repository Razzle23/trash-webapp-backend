from pydantic import BaseModel, Field

class MeResponse(BaseModel):
    id: int
    telegram_id: int
    name: str
    role: str
    is_admin: bool
    is_blocked: bool
    house_id: int | None
    executor_online: bool

class CustomerProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    house_id: int
    entrance: str = Field(min_length=1, max_length=8)
    floor: str = Field(min_length=1, max_length=8)
    apartment: str = Field(min_length=1, max_length=12)
    comment: str | None = Field(default=None, max_length=300)