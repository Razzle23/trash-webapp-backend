import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, Text, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserRole(str, enum.Enum):
    customer = "customer"
    executor = "executor"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)

    name: Mapped[str] = mapped_column(Text, nullable=False)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        server_default="customer",
    )

    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    house_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("houses.id"), nullable=True)

    entrance: Mapped[str | None] = mapped_column(Text, nullable=True)
    floor: Mapped[str | None] = mapped_column(Text, nullable=True)
    apartment: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    executor_online: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    executor_online_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executor_offline_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())