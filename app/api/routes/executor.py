from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user_id
from app.models.user import User, UserRole
from app.models.house import House
from app.models.order import Order, OrderStatus
from app.schemas.executor import (
    ExecutorHouseSet,
    ExecutorInboxResponse,
    ExecutorOrderCard,
    ExecutorAcceptResponse,
)
from app.services.order_assigner import assign_pending_orders, get_int_setting

router = APIRouter(prefix="/executor", tags=["executor"])


def _to_card(o: Order) -> ExecutorOrderCard:
    return ExecutorOrderCard(
        id=o.id,
        public_number=o.public_number,
        status=o.status.value,
        scheduled_at=o.scheduled_at,
        entrance=o.entrance,
        floor=o.floor,
        apartment=o.apartment,
        comment=o.comment,
        bags=o.bags,
        price=o.price,
        payment=o.payment.value,
        created_at=o.created_at,
    )


async def _get_executor_or_403(db: AsyncSession, user_id: int) -> User:
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != UserRole.executor:
        raise HTTPException(status_code=403, detail="Only executors can access this endpoint")
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="User is blocked")
    return user


async def _reassign_offline_accepted(db: AsyncSession) -> None:
    """
    Если исполнитель офлайн 10+ минут, его accepted-заказы снова становятся created.
    """
    ten_min_ago = datetime.now(timezone.utc) - timedelta(minutes=10)

    stmt = (
        update(Order)
        .where(
            Order.status == OrderStatus.accepted,
            Order.executor_id.isnot(None),
            Order.executor_id.in_(
                select(User.id).where(
                    User.role == UserRole.executor,
                    User.executor_online == False,  # noqa: E712
                    User.executor_offline_since.isnot(None),
                    User.executor_offline_since <= ten_min_ago,
                )
            ),
        )
        .values(
            executor_id=None,
            status=OrderStatus.created,
            assigned_executor_id=None,
            assigned_at=None,
            reassign_count=Order.reassign_count + 1,
            last_reassigned_at=func.now(),
        )
    )
    await db.execute(stmt)
    await db.commit()


@router.put("/house")
async def set_executor_house(
    payload: ExecutorHouseSet,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    user = await _get_executor_or_403(db, user_id)

    if user.executor_online:
        raise HTTPException(status_code=409, detail="Executor must be offline to change house")

    house = await db.scalar(
        select(House).where(House.id == payload.house_id, House.is_active == True)  # noqa: E712
    )
    if not house:
        raise HTTPException(status_code=400, detail="House not found or inactive")

    user.house_id = payload.house_id
    await db.commit()

    return {"ok": True, "house_id": user.house_id}


@router.post("/online")
async def go_online(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    user = await _get_executor_or_403(db, user_id)

    if not user.house_id:
        raise HTTPException(status_code=400, detail="Select house first")

    house = await db.scalar(
        select(House).where(House.id == user.house_id, House.is_active == True)  # noqa: E712
    )
    if not house:
        raise HTTPException(status_code=400, detail="House not found or inactive")

    online_cnt = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.role == UserRole.executor,
            User.house_id == user.house_id,
            User.executor_online == True,  # noqa: E712
            User.is_blocked == False,      # noqa: E712
        )
    )
    online_cnt = online_cnt or 0

    if online_cnt >= house.executor_limit and not user.executor_online:
        raise HTTPException(status_code=409, detail="Executor limit reached for this house")

    user.executor_online = True
    user.executor_online_since = datetime.now(timezone.utc)
    user.executor_offline_since = None
    await db.commit()

    # как только исполнитель вышел онлайн — пробуем назначить pending-заказы этого дома
    await assign_pending_orders(db, user.house_id)

    return {"ok": True, "house_id": user.house_id, "executor_online": True}


@router.post("/offline")
async def go_offline(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    user = await _get_executor_or_403(db, user_id)

    user.executor_online = False
    user.executor_offline_since = datetime.now(timezone.utc)
    await db.commit()

    return {"ok": True, "executor_online": False}


@router.get("/inbox", response_model=ExecutorInboxResponse)
async def inbox(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    user = await _get_executor_or_403(db, user_id)

    if not user.house_id:
        raise HTTPException(status_code=400, detail="Select house first")

    # 1) вернуть в пул зависшие accepted у офлайн исполнителей
    await _reassign_offline_accepted(db)

    # 2) назначить pending created по дому
    await assign_pending_orders(db, user.house_id)

    assigned_created = (
        await db.scalars(
            select(Order)
            .where(
                Order.house_id == user.house_id,
                Order.status == OrderStatus.created,
                Order.executor_id.is_(None),
                Order.assigned_executor_id == user.id,
            )
            .order_by(Order.created_at.asc())
        )
    ).all()

    my_active = (
        await db.scalars(
            select(Order)
            .where(
                Order.executor_id == user.id,
                Order.status == OrderStatus.accepted,
            )
            .order_by(Order.accepted_at.asc().nulls_last())
        )
    ).all()

    return ExecutorInboxResponse(
        house_id=user.house_id,
        assigned_created=[_to_card(o) for o in assigned_created],
        my_active=[_to_card(o) for o in my_active],
    )


@router.post("/orders/{order_id}/accept", response_model=ExecutorAcceptResponse)
async def accept_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    user = await _get_executor_or_403(db, user_id)

    if not user.house_id:
        raise HTTPException(status_code=400, detail="Select house first")

    max_active = await get_int_setting(db, "max_active_orders_per_executor", 3)

    active_cnt = await db.scalar(
        select(func.count())
        .select_from(Order)
        .where(
            Order.executor_id == user.id,
            Order.status == OrderStatus.accepted,
        )
    )
    active_cnt = active_cnt or 0

    if active_cnt >= max_active:
        raise HTTPException(status_code=409, detail="Active orders limit reached")

    stmt = (
        update(Order)
        .where(
            Order.id == order_id,
            Order.house_id == user.house_id,
            Order.status == OrderStatus.created,
            Order.executor_id.is_(None),
            Order.assigned_executor_id == user.id,
        )
        .values(
            executor_id=user.id,
            status=OrderStatus.accepted,
            accepted_at=func.now(),
        )
        .returning(Order.id, Order.status)
    )

    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(status_code=409, detail="Order cannot be accepted")

    await db.commit()
    return ExecutorAcceptResponse(id=row[0], status=row[1].value)


@router.post("/orders/{order_id}/complete", response_model=ExecutorAcceptResponse)
async def complete_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    user = await _get_executor_or_403(db, user_id)

    stmt = (
        update(Order)
        .where(
            Order.id == order_id,
            Order.executor_id == user.id,
            Order.status == OrderStatus.accepted,
        )
        .values(
            status=OrderStatus.done,
            completed_at=func.now(),
        )
        .returning(Order.id, Order.status)
    )

    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(status_code=409, detail="Order cannot be completed")

    await db.commit()
    return ExecutorAcceptResponse(id=row[0], status=row[1].value)