from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user_id
from app.models.user import User


async def require_admin(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> User:
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="User is blocked")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return user