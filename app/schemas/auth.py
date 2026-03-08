from pydantic import BaseModel


class AuthRequest(BaseModel):
    initData: str


class AuthResponse(BaseModel):
    token: str