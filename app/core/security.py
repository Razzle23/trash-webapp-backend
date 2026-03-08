from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.config import settings


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRES_MINUTES)
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> str:
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    sub = payload.get("sub")
    if not sub:
        raise ValueError("Invalid token")
    return str(sub)