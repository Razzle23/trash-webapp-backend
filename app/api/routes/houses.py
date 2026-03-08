from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.models.house import House
from app.schemas.house import HouseOut

router = APIRouter(prefix="/houses", tags=["houses"])


@router.get("", response_model=list[HouseOut])
async def list_houses(db: AsyncSession = Depends(get_db)):
    res = await db.scalars(select(House).where(House.is_active == True).order_by(House.id))
    houses = res.all()
    return [HouseOut(id=h.id, title=h.title, district_id=h.district_id, executor_limit=h.executor_limit) for h in houses]