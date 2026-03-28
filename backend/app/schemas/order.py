from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.order import DeliveryType, OrderOrigin, OrderStatus, PaymentMethod, PaymentStatus


class OrderItemCreate(BaseModel):
    """Línea de un pedido al crearlo."""

    product_id: int | None = None
    combo_id: int | None = None
    # Tamaño de pizza: 'large' o 'small'. Null para empanadas y bebidas.
    size: str | None = None
    # Segundo producto para pedidos mitad y mitad (solo cuando hay product_id)
    second_product_id: int | None = None
    quantity: int = 1
    unit_price: float
    notes: str | None = None


class OrderItemRead(BaseModel):
    id: int
    order_id: int
    product_id: int | None
    combo_id: int | None
    size: str | None
    second_product_id: int | None
    quantity: int
    unit_price: float
    notes: str | None

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    """Datos para crear un pedido."""

    customer_id: int
    origin: OrderOrigin
    delivery_type: DeliveryType | None = None
    delivery_address: str | None = None
    whatsapp_number_id: int | None = None
    notes: str | None = None
    items: list[OrderItemCreate] = []


class OrderRead(BaseModel):
    """Representación pública de un pedido."""

    id: int
    pizzeria_id: int
    customer_id: int
    whatsapp_number_id: int | None
    origin: OrderOrigin
    status: OrderStatus
    delivery_type: DeliveryType | None
    delivery_address: str | None
    total: float
    notes: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead] = []

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    """Transición de estado de un pedido."""

    status: OrderStatus


class PaymentCreate(BaseModel):
    """Registro de un pago asociado a un pedido."""

    method: PaymentMethod
    amount: float
    external_reference: str | None = None


class PaymentRead(BaseModel):
    id: int
    order_id: int
    pizzeria_id: int
    method: PaymentMethod
    status: PaymentStatus
    amount: float
    external_reference: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentCreate(BaseModel):
    """Registro de una incidencia en un pedido."""

    type: str
    description: str | None = None


class IncidentResolve(BaseModel):
    """Datos de resolución de una incidencia."""

    resolution_notes: str | None = None


class IncidentRead(BaseModel):
    id: int
    order_id: int
    pizzeria_id: int
    type: str
    description: str | None
    is_resolved: bool
    reported_by_id: int | None
    resolved_by_id: int | None
    resolved_at: datetime | None
    resolution_notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
