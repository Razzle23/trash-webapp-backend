from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.core.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


def get_current_user_id(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    try:
        sub = decode_token(creds.credentials)
        return int(sub)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")