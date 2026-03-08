from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, Text, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class House(Base):
    __tablename__ = "houses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    district_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("districts.id"), nullable=True)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    executor_limit: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())