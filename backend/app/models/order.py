from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.account import Pizzeria
    from app.models.customer import Customer
    from app.models.whatsapp import WhatsAppNumber


class OrderOrigin(str, enum.Enum):
    whatsapp = "whatsapp"
    phone = "phone"
    operator = "operator"


class OrderStatus(str, enum.Enum):
    in_progress = "in_progress"
    pending_payment = "pending_payment"
    pending_preparation = "pending_preparation"
    in_preparation = "in_preparation"
    ready_for_dispatch = "ready_for_dispatch"
    in_delivery = "in_delivery"
    delivered = "delivered"
    cancelled = "cancelled"
    with_incident = "with_incident"
    discarded = "discarded"


class PaymentMethod(str, enum.Enum):
    cash = "cash"
    transfer = "transfer"
    mercadopago = "mercadopago"
    credit = "credit"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"
    refunded = "refunded"


class Order(Base, TimestampMixin, SoftDeleteMixin):
    """Pedido de un cliente en una pizzería."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    pizzeria_id: Mapped[int] = mapped_column(ForeignKey("pizzerias.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    whatsapp_number_id: Mapped[int | None] = mapped_column(
        ForeignKey("whatsapp_numbers.id"), nullable=True
    )
    origin: Mapped[OrderOrigin] = mapped_column(
        Enum(OrderOrigin, name="order_origin"), nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"),
        default=OrderStatus.in_progress,
        nullable=False,
    )
    total: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    pizzeria: Mapped[Pizzeria] = relationship(back_populates="orders")
    customer: Mapped[Customer] = relationship(back_populates="orders")
    whatsapp_number: Mapped[WhatsAppNumber | None] = relationship(back_populates="orders")
    items: Mapped[list[OrderItem]] = relationship(back_populates="order")
    payments: Mapped[list[Payment]] = relationship(back_populates="order")
    incidents: Mapped[list[Incident]] = relationship(back_populates="order")


class OrderItem(Base):
    """Línea de un pedido. Puede ser producto o combo, nunca ambos."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    combo_id: Mapped[int | None] = mapped_column(ForeignKey("combos.id"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    order: Mapped[Order] = relationship(back_populates="items")


class Payment(Base, TimestampMixin):
    """Pago asociado a un pedido."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    pizzeria_id: Mapped[int] = mapped_column(ForeignKey("pizzerias.id"), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method"), nullable=False
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status"),
        default=PaymentStatus.pending,
        nullable=False,
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(255))

    order: Mapped[Order] = relationship(back_populates="payments")


class Incident(Base, TimestampMixin):
    """Incidencia durante o después del delivery."""

    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    pizzeria_id: Mapped[int] = mapped_column(ForeignKey("pizzerias.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_resolved: Mapped[bool] = mapped_column(default=False, nullable=False)

    order: Mapped[Order] = relationship(back_populates="incidents")
