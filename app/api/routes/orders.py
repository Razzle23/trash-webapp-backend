from datetime import datetime, time, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user_id
from app.models.user import User, UserRole
from app.models.order import Order, PaymentMethod, OrderStatus
from app.schemas.order import OrderCreate, OrderOut

from zoneinfo import ZoneInfo

router = APIRouter(prefix="/orders", tags=["orders"])

SERVICE_TZ = ZoneInfo("Europe/Amsterdam")


def slot_start(now_local, slot):
    from datetime import datetime, timedelta

    d = now_local.date()

    if slot == "morning":
        # сегодня 06:00
        start_today = datetime(d.year, d.month, d.day, 6, 0, tzinfo=SERVICE_TZ)
        end_today = datetime(d.year, d.month, d.day, 8, 0, tzinfo=SERVICE_TZ)

        if now_local < end_today:
            return start_today

        # завтра
        d2 = d + timedelta(days=1)
        return datetime(d2.year, d2.month, d2.day, 6, 0, tzinfo=SERVICE_TZ)

    if slot == "evening":
        # сегодня 21:00
        start_today = datetime(d.year, d.month, d.day, 21, 0, tzinfo=SERVICE_TZ)
        end_today = datetime(d.year, d.month, d.day, 23, 0, tzinfo=SERVICE_TZ)

        if now_local < end_today:
            return start_today

        # завтра
        d2 = d + timedelta(days=1)
        return datetime(d2.year, d2.month, d2.day, 21, 0, tzinfo=SERVICE_TZ)

def calc_price(bags: int) -> int:
    return {1: 70, 2: 90, 3: 110}[bags]


def validate_time_windows(now_local: datetime, scheduled_local: datetime) -> None:
    """
    Окна выполнения:
      - 06:00–08:00
      - 21:00–23:00
    Ограничение приёма:
      - утро: до 07:00
      - вечер: до 22:00
    """
    t = scheduled_local.time()

    in_morning = time(6, 0) <= t <= time(8, 0)
    in_evening = time(21, 0) <= t <= time(23, 0)

    if not (in_morning or in_evening):
        raise HTTPException(status_code=400, detail="scheduled_at must be within 06:00–08:00 or 21:00–23:00")

    # прием заказов по текущему времени (в той же локальной зоне)
    now_t = now_local.time()

    if in_morning:
        if now_t > time(7, 0):
            raise HTTPException(status_code=400, detail="Morning orders are accepted only until 07:00")
    if in_evening:
        if now_t > time(22, 0):
            raise HTTPException(status_code=400, detail="Evening orders are accepted only until 22:00")


@router.post("", response_model=OrderOut)
async def create_order(
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != UserRole.customer:
        raise HTTPException(status_code=403, detail="Only customers can create orders")
    if not user.house_id or not user.entrance or not user.floor or not user.apartment:
        raise HTTPException(status_code=400, detail="Customer profile is incomplete")

    # payment
    try:
        payment = PaymentMethod(payload.payment)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payment method")

    # time slot -> scheduled_at (start of window, today or tomorrow)
    now_local = datetime.now(SERVICE_TZ)
    if payload.time_slot not in ("morning", "evening"):
        raise HTTPException(status_code=400, detail="time_slot must be morning or evening")

    scheduled_local = slot_start(now_local, payload.time_slot)

    # price
    try:
        price = calc_price(payload.bags)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid bags value")

    public_number = int(datetime.now(timezone.utc).timestamp())

    order = Order(
        public_number=public_number,
        customer_id=user.id,
        executor_id=None,
        assigned_executor_id=None,
        house_id=user.house_id,
        entrance=user.entrance,
        floor=user.floor,
        apartment=user.apartment,
        comment=user.comment,
        bags=payload.bags,
        price=price,
        payment=payment,
        status=OrderStatus.created,
        scheduled_at=scheduled_local,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    from app.services.order_assigner import assign_pending_orders
    await assign_pending_orders(db, user.house_id)

    await db.refresh(order)

    return OrderOut(
        id=order.id,
        public_number=order.public_number,
        status=order.status.value,
        scheduled_at=order.scheduled_at,
        price=order.price,
        payment=order.payment.value,
        bags=order.bags,
        created_at=order.created_at,
    )


@router.get("", response_model=list[OrderOut])
async def list_orders(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    q = select(Order).where(Order.customer_id == user.id).order_by(desc(Order.created_at)).limit(50)
    res = await db.scalars(q)
    items = res.all()

    return [
        OrderOut(
            id=o.id,
            public_number=o.public_number,
            status=o.status.value,
            scheduled_at=o.scheduled_at,
            price=o.price,
            payment=o.payment.value,
            bags=order.bags,
            created_at=o.created_at,
        )
        for o in items
    ]

@router.get("/active", response_model=OrderOut | None)
async def get_active_order(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    order = await db.scalar(
        select(Order)
        .where(
            Order.customer_id == user.id,
            Order.status.in_([OrderStatus.created, OrderStatus.accepted])
        )
        .order_by(Order.created_at.desc())
    )

    if not order:
        return None

    return OrderOut(
        id=order.id,
        public_number=order.public_number,
        status=order.status.value,
        scheduled_at=order.scheduled_at,
        price=order.price,
        payment=order.payment.value,
        bags=order.bags,
        created_at=order.created_at,
    )

@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    order = await db.scalar(select(Order).where(Order.id == order_id, Order.customer_id == user.id))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderOut(
        id=order.id,
        public_number=order.public_number,
        status=order.status.value,
        scheduled_at=order.scheduled_at,
        price=order.price,
        payment=order.payment.value,
        bags=order.bags,
        created_at=order.created_at,
    )

