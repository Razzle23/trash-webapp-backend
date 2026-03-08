from pydantic import BaseModel


class DistrictOut(BaseModel):
    id: int
    title: str