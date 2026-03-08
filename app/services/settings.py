from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.setting import Setting


async def get_int_setting(db: AsyncSession, key: str, default: int) -> int:
    row = await db.scalar(select(Setting).where(Setting.key == key))
    if not row:
        return default
    try:
        return int(row.value)
    except Exception:
        return default