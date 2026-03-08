from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user_id
from app.models.user import User, UserRole
from app.models.house import House
from app.schemas.user import CustomerProfileUpdate, MeResponse

router = APIRouter(prefix="/me", tags=["me"])


@router.put("/customer", response_model=MeResponse)
async def update_customer_profile(
    payload: CustomerProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role != UserRole.customer:
        raise HTTPException(status_code=403, detail="Only customers can update this profile")

    house = await db.scalar(select(House).where(House.id == payload.house_id, House.is_active == True))
    if not house:
        raise HTTPException(status_code=400, detail="House not found or inactive")

    user.name = payload.name
    user.house_id = payload.house_id
    user.entrance = payload.entrance
    user.floor = payload.floor
    user.apartment = payload.apartment
    user.comment = payload.comment

    await db.commit()
    await db.refresh(user)

    return MeResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        name=user.name,
        role=user.role.value,
        is_admin=user.is_admin,
        is_blocked=user.is_blocked,
        house_id=user.house_id,
        executor_online=user.executor_online,
    )   