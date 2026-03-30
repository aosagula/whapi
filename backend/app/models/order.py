from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


ORDER_STATUS_ENUM = sa.Enum(
    "in_progress",           # el cliente está armando el pedido en el chatbot
    "pending_payment",       # esperando confirmación del pago online (MercadoPago)
    "pending_preparation",   # pago confirmado, a la espera de cocina
    "in_preparation",        # el cocinero tomó el pedido
    "to_dispatch",           # pedido listo, esperando repartidor
    "in_delivery",           # repartidor en camino
    "delivered",             # entregado correctamente (estado final exitoso)
    "cancelled",             # cancelado (ver payment_status para política de reembolso)
    "with_incident",         # problema durante o después del delivery
    "discarded",             # descartado por inactividad (nunca se confirmó)
    name="order_status"
)

PAYMENT_STATUS_ENUM = sa.Enum(
    "paid",               # pago confirmado
    "cash_on_delivery",   # efectivo al momento de la entrega
    "pending_payment",    # link MP enviado, sin confirmación aún
    "credit",             # cancelado: monto acreditado para próxima compra
    "refunded",           # reembolso manual por el administrador
    "no_charge",          # cancelado antes de generar cobro
    name="payment_status"
)

ORDER_ORIGIN_ENUM = sa.Enum(
    "whatsapp", "phone", "operator",
    name="order_origin"
)

DELIVERY_TYPE_ENUM = sa.Enum(
    "delivery", "pickup",
    name="delivery_type"
)

PAYMENT_METHOD_ENUM = sa.Enum(
    "mercadopago", "cash", "transfer",
    name="payment_method"
)

MP_PAYMENT_STATUS_ENUM = sa.Enum(
    "pending", "approved", "rejected", "refunded",
    name="mp_payment_status"
)

INCIDENT_TYPE_ENUM = sa.Enum(
    "wrong_address",
    "wrong_order",
    "missing_item",
    "bad_condition",
    "customer_not_found",
    "other",
    name="incident_type"
)

INCIDENT_STATUS_ENUM = sa.Enum(
    "open",
    "in_review",
    "resolved_redispatch",
    "resolved_cancel",
    name="incident_status"
)


class Order(Base):
    """Pedido de un cliente en un comercio."""

    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Número visible de pedido (secuencial por comercio, gestionado a nivel app)
    order_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("conversation_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        ORDER_STATUS_ENUM, default="in_progress", nullable=False, index=True
    )
    payment_status: Mapped[str] = mapped_column(
        PAYMENT_STATUS_ENUM, default="no_charge", nullable=False
    )
    # Origen del pedido: siempre se registra
    origin: Mapped[str] = mapped_column(ORDER_ORIGIN_ENUM, nullable=False)
    delivery_type: Mapped[str] = mapped_column(DELIVERY_TYPE_ENUM, nullable=False)
    delivery_address: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    total_amount: Mapped[float] = mapped_column(sa.Numeric(10, 2), nullable=False)
    # Crédito del cliente aplicado a este pedido
    credit_applied: Mapped[float] = mapped_column(
        sa.Numeric(10, 2), default=0, nullable=False
    )
    # Repartidor asignado (empleado con rol delivery)
    delivery_person_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Notas internas del equipo (no visibles al cliente)
    internal_notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # Operador que creó el pedido (solo en pedidos telefónicos/operador)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    # Relaciones
    items: Mapped[list[OrderItem]] = relationship("OrderItem", back_populates="order")
    payments: Mapped[list[Payment]] = relationship("Payment", back_populates="order")
    incidents: Mapped[list[Incident]] = relationship("Incident", back_populates="order")
    status_history: Mapped[list[OrderStatusHistory]] = relationship(
        "OrderStatusHistory", back_populates="order", order_by="OrderStatusHistory.changed_at"
    )
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")  # noqa: F821


class OrderItem(Base):
    """Ítem individual dentro de un pedido."""

    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Producto individual o combo (uno de los dos debe estar presente)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=True,
    )
    combo_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("combos.id", ondelete="RESTRICT"),
        nullable=True,
    )
    quantity: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(sa.Numeric(10, 2), nullable=False)
    # Variante en JSON: tamaño, mitad y mitad, etc.
    # Ej: {"size": "large", "half1": "PIZ-MOZ", "half2": "PIZ-FUG"}
    variant: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    # Relaciones
    order: Mapped[Order] = relationship("Order", back_populates="items")


class Payment(Base):
    """Pago asociado a un pedido."""

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    method: Mapped[str] = mapped_column(PAYMENT_METHOD_ENUM, nullable=False)
    amount: Mapped[float] = mapped_column(sa.Numeric(10, 2), nullable=False)
    # IDs de MercadoPago (solo para método mercadopago)
    mp_preference_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    mp_payment_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        MP_PAYMENT_STATUS_ENUM, default="pending", nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, nullable=False
    )

    # Relaciones
    order: Mapped[Order] = relationship("Order", back_populates="payments")


class Incident(Base):
    """Incidencia reportada durante o después del delivery."""

    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(INCIDENT_TYPE_ENUM, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # Usuario que reportó la incidencia (repartidor, cajero, etc.)
    reported_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        INCIDENT_STATUS_ENUM, default="open", nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    # Relaciones
    order: Mapped[Order] = relationship("Order", back_populates="incidents")


class OrderStatusHistory(Base):
    """Historial de cambios de estado de un pedido."""

    __tablename__ = "order_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # create_type=False porque el ENUM order_status ya fue creado en la migración 0001
    previous_status: Mapped[str | None] = mapped_column(
        sa.Enum(
            "in_progress", "pending_payment", "pending_preparation",
            "in_preparation", "to_dispatch", "in_delivery",
            "delivered", "cancelled", "with_incident", "discarded",
            name="order_status", create_type=False,
        ),
        nullable=True,
    )
    new_status: Mapped[str] = mapped_column(
        sa.Enum(
            "in_progress", "pending_payment", "pending_preparation",
            "in_preparation", "to_dispatch", "in_delivery",
            "delivered", "cancelled", "with_incident", "discarded",
            name="order_status", create_type=False,
        ),
        nullable=False,
    )
    # Usuario que efectuó el cambio (None = sistema automático)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    changed_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, nullable=False
    )
    note: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    # Relaciones
    order: Mapped[Order] = relationship("Order", back_populates="status_history")
