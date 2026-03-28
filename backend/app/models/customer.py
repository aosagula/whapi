from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Customer(Base):
    """Cliente de un comercio, identificado por su número de WhatsApp.

    El mismo número puede existir como clientes distintos en distintos comercios.
    """

    __tablename__ = "customers"
    __table_args__ = (
        # Un cliente es único por teléfono dentro del mismo comercio
        sa.UniqueConstraint("business_id", "phone", name="uq_customer_phone_per_business"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phone: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    # Nombre obtenido del chatbot en el primer pedido
    name: Mapped[str | None] = mapped_column(sa.String(150), nullable=True)
    address: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # Saldo de crédito a favor (por cancelaciones)
    credit_balance: Mapped[float] = mapped_column(
        sa.Numeric(10, 2), default=0, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    # Relaciones
    credits: Mapped[list[Credit]] = relationship("Credit", back_populates="customer")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="customer")  # noqa: F821


class Credit(Base):
    """Movimiento de crédito de un cliente (positivo = acredita, negativo = usa)."""

    __tablename__ = "credits"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[float] = mapped_column(sa.Numeric(10, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    # Pedido que originó el movimiento (nullable: puede ser ajuste manual)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, nullable=False
    )

    # Relaciones
    customer: Mapped[Customer] = relationship("Customer", back_populates="credits")
