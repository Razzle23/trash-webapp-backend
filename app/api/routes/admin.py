from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.admin_deps import require_admin
from app.models.order import Order, OrderStatus
from app.models.user import User, UserRole
from app.schemas.admin import LiveStatsOut, AdminExecutorOut, AdminOrderOut, CancelReq

router = APIRouter(prefix="/admin", tags=["admin"])


def _order_out(o: Order) -> AdminOrderOut:
    return AdminOrderOut(
        id=o.id,
        public_number=o.public_number,
        status=o.status.value,
        house_id=o.house_id,
        entrance=o.entrance,
        floor=o.floor,
        apartment=o.apartment,
        comment=o.comment,
        bags=o.bags,
        price=o.price,
        payment=o.payment.value,
        scheduled_at=o.scheduled_at,
        customer_id=o.customer_id,
        executor_id=o.executor_id,
        created_at=o.created_at,
        assigned_executor_id=o.assigned_executor_id,
        assigned_at=o.assigned_at,
    )


@router.get("/houses/{house_id}/live-stats", response_model=LiveStatsOut)
async def live_stats(
    house_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    row = (await db.execute(
        select(
            func.count().filter(Order.status == OrderStatus.created).label("unaccepted"),
            func.count().filter(Order.status == OrderStatus.accepted).label("accepted"),
        ).where(Order.house_id == house_id)
    )).first()

    return LiveStatsOut(house_id=house_id, unaccepted=int(row.unaccepted), accepted=int(row.accepted))


@router.get("/executors", response_model=list[AdminExecutorOut])
async def list_executors(
    house_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    q = select(User).where(User.role == UserRole.executor, User.is_blocked == False)  # noqa: E712
    if house_id is not None:
        q = q.where(User.house_id == house_id)

    users = (await db.scalars(q.order_by(User.id))).all()

    out: list[AdminExecutorOut] = []
    for u in users:
        active = await db.scalar(
            select(func.count()).select_from(Order).where(Order.executor_id == u.id, Order.status == OrderStatus.accepted)
        )
        out.append(
            AdminExecutorOut(
                id=u.id,
                name=u.name,
                house_id=u.house_id,
                online=u.executor_online,
                active_accepted=int(active or 0),
            )
        )
    return out


@router.get("/orders/by-number/{public_number}", response_model=AdminOrderOut)
async def get_order_by_number(
    public_number: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    order = await db.scalar(select(Order).where(Order.public_number == public_number))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_out(order)


@router.post("/orders/{order_id}/confirm", response_model=AdminOrderOut)
async def admin_confirm(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    stmt = (
        update(Order)
        .where(Order.id == order_id, Order.status.in_([OrderStatus.done, OrderStatus.accepted]))
        .values(status=OrderStatus.confirmed, confirmed_at=func.now())
        .returning(Order)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(status_code=409, detail="Order cannot be confirmed")
    await db.commit()
    return _order_out(row[0])


@router.post("/orders/{order_id}/cancel", response_model=AdminOrderOut)
async def admin_cancel(
    order_id: int,
    payload: CancelReq,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    stmt = (
        update(Order)
        .where(Order.id == order_id, Order.status != OrderStatus.confirmed)
        .values(
            status=OrderStatus.cancelled,
            cancelled_at=func.now(),
            cancelled_by="admin",
            cancel_reason=payload.reason,
            executor_id=None,
            assigned_executor_id=None,
            assigned_at=None,
        )
        .returning(Order)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(status_code=409, detail="Order cannot be cancelled")
    await db.commit()
    return _order_out(row[0])


@router.post("/orders/{order_id}/reassign", response_model=AdminOrderOut)
async def admin_reassign(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    stmt = (
        update(Order)
        .where(Order.id == order_id, Order.status.notin_([OrderStatus.confirmed, OrderStatus.cancelled]))
        .values(
            executor_id=None,
            status=OrderStatus.created,
            assigned_executor_id=None,
            assigned_at=None,
            reassign_count=Order.reassign_count + 1,
            last_reassigned_at=func.now(),
        )
        .returning(Order)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(status_code=409, detail="Order cannot be reassigned")
    await db.commit()
    # попробуем сразу распределить created заказы по подъездам
    from app.api.routes.executor import _assign_created_orders_for_house  # локальный импорт
    await _assign_created_orders_for_house(db, user.house_id)

    # обновим заказ, чтобы вернуть assigned_executor_id (если назначился)
    await db.refresh(order)
    return _order_out(row[0])