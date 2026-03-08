import enum
from datetime import datetime

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, Text, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PaymentMethod(str, enum.Enum):
    cash = "cash"
    transfer = "transfer"
    sbp = "sbp"


class OrderStatus(str, enum.Enum):
    created = "created"
    accepted = "accepted"
    done = "done"
    confirmed = "confirmed"
    cancelled = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    public_number: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)

    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    executor_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)

    assigned_executor_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    house_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("houses.id"), nullable=False)

    entrance: Mapped[str] = mapped_column(Text, nullable=False)
    floor: Mapped[str] = mapped_column(Text, nullable=False)
    apartment: Mapped[str] = mapped_column(Text, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    bags: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)

    payment: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method"),
        nullable=False,
    )

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"),
        nullable=False,
        server_default="created",
    )

    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reassign_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_reassigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    cancelled_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)