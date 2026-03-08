from pydantic import BaseModel


class HouseOut(BaseModel):
    id: int
    title: str
    district_id: int | None
    executor_limit: int