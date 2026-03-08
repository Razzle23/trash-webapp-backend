from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.models.user import User, UserRole
from app.models.setting import Setting


async def get_int_setting(db: AsyncSession, key: str, default: int) -> int:
    row = await db.scalar(select(Setting).where(Setting.key == key))
    if not row:
        return default
    try:
        return int(row.value)
    except Exception:
        return default


async def assign_pending_orders(db: AsyncSession, house_id: int | None = None) -> None:
    """
    Назначает created-заказы онлайн-исполнителям по дому.
    Если house_id передан — работает только по одному дому.
    """

    max_active = await get_int_setting(db, "max_active_orders_per_executor", 3)

    q = select(Order).where(
        Order.status == OrderStatus.created,
        Order.executor_id.is_(None),
    )

    if house_id is not None:
        q = q.where(Order.house_id == house_id)

    q = q.order_by(Order.created_at.asc())

    orders = (await db.scalars(q)).all()

    for order in orders:
        executors = (
            await db.scalars(
                select(User)
                .where(
                    User.role == UserRole.executor,
                    User.executor_online == True,   # noqa: E712
                    User.house_id == order.house_id,
                    User.is_blocked == False,       # noqa: E712
                )
                .order_by(User.id.asc())
            )
        ).all()

        if not executors:
            continue

        for executor in executors:
            active_cnt = await db.scalar(
                select(func.count())
                .select_from(Order)
                .where(
                    Order.executor_id == executor.id,
                    Order.status == OrderStatus.accepted,
                )
            )
            active_cnt = active_cnt or 0

            if active_cnt < max_active:
                order.assigned_executor_id = executor.id
                break

    await db.commit()