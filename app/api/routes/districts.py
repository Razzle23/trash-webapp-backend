from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.models.district import District
from app.schemas.district import DistrictOut

router = APIRouter(prefix="/districts", tags=["districts"])


@router.get("", response_model=list[DistrictOut])
async def list_districts(db: AsyncSession = Depends(get_db)):
    res = await db.scalars(select(District).where(District.is_active == True).order_by(District.id))
    districts = res.all()
    return [DistrictOut(id=d.id, title=d.title) for d in districts]