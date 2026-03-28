from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Pizzeria
    from app.models.order import Order
    from app.models.conversation import ChatSession


class Customer(Base, TimestampMixin):
    """Cliente de una pizzería. Scoped por pizzeria_id."""

    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("pizzeria_id", "phone", name="uq_customer_pizzeria_phone"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pizzeria_id: Mapped[int] = mapped_column(ForeignKey("pizzerias.id"), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str | None] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    has_whatsapp: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    pizzeria: Mapped[Pizzeria] = relationship(back_populates="customers")
    credit: Mapped[CustomerCredit | None] = relationship(
        back_populates="customer", uselist=False
    )
    orders: Mapped[list[Order]] = relationship(back_populates="customer")
    chat_sessions: Mapped[list[ChatSession]] = relationship(back_populates="customer")


class CustomerCredit(Base):
    """Saldo a favor del cliente en una pizzería específica."""

    __tablename__ = "customer_credits"

    id: Mapped[int] = mapped_column(primary_key=True)
    pizzeria_id: Mapped[int] = mapped_column(ForeignKey("pizzerias.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"), unique=True, nullable=False
    )
    balance: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer: Mapped[Customer] = relationship(back_populates="credit")
