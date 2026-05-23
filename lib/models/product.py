import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from lib.database.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    stock_qty: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
