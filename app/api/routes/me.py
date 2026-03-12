from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user_id
from app.models.user import User
from app.schemas.user import MeResponse

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=MeResponse)
async def me(db: AsyncSession = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return MeResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        name=user.name,
        role=user.role.value,
        is_admin=user.is_admin,
        is_blocked=user.is_blocked,
        house_id=user.house_id,
        executor_online=user.executor_online,
        entrance=user.entrance,
        floor=user.floor,
        apartment=user.apartment,
        comment=user.comment,
    )