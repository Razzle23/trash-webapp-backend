from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Text, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class District(Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())