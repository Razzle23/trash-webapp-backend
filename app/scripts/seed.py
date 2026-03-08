import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.district import District
from app.models.house import House
from app.models.setting import Setting


async def main():
    async with AsyncSessionLocal() as db:
        # settings
        s = await db.scalar(select(Setting).where(Setting.key == "max_active_orders_per_executor"))
        if not s:
            db.add(Setting(key="max_active_orders_per_executor", value="3"))

        # districts
        d1 = await db.scalar(select(District).where(District.title == "Район 1"))
        if not d1:
            d1 = District(title="Район 1")
            db.add(d1)
            await db.flush()

        # houses
        h = await db.scalar(select(House).where(House.title == "Дом 1"))
        if not h:
            db.add(House(title="Дом 1", district_id=d1.id, executor_limit=3, is_active=True))

        await db.commit()
        print("Seed done")


if __name__ == "__main__":
    asyncio.run(main())