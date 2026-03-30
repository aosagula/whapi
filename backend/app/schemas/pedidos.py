"""Schemas Pydantic para el módulo de pedidos."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Items del pedido ──────────────────────────────────────────────────────────

class OrderItemBase(BaseModel):
    product_id: uuid.UUID | None = None
    combo_id: uuid.UUID | None = None
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)
    variant: dict[str, Any] | None = None
    notes: str | None = None


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: uuid.UUID
    # Nombre descriptivo para mostrar en el detalle
    display_name: str | None = None

    model_config = {"from_attributes": True}


# ── Historial de estados ──────────────────────────────────────────────────────

class StatusHistoryResponse(BaseModel):
    id: uuid.UUID
    previous_status: str | None
    new_status: str
    changed_by: uuid.UUID | None
    changed_by_name: str | None = None
    changed_at: datetime
    note: str | None

    model_config = {"from_attributes": True}


# ── Incidencias ───────────────────────────────────────────────────────────────

class IncidentCreate(BaseModel):
    type: str
    description: str | None = None


class IncidentResponse(BaseModel):
    id: uuid.UUID
    type: str
    description: str | None
    reported_by: uuid.UUID | None
    reported_by_name: str | None = None
    status: str
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Pedido ────────────────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    customer_id: uuid.UUID
    origin: str = "operator"
    delivery_type: str
    delivery_address: str | None = None
    payment_status: str = "no_charge"
    total_amount: float = Field(ge=0)
    credit_applied: float = Field(ge=0, default=0)
    kitchen_notes: str | None = None
    delivery_notes: str | None = None
    items: list[OrderItemCreate]


class OrderUpdateStatus(BaseModel):
    status: str
    note: str | None = None


class OrderUpdatePayment(BaseModel):
    payment_status: str


class OrderAssignDelivery(BaseModel):
    delivery_person_id: uuid.UUID | None


class OrderUpdateNotes(BaseModel):
    internal_notes: str | None


class OrderCancel(BaseModel):
    # Si None, la policy se calcula automáticamente según el estado actual
    payment_policy: str | None = None
    note: str | None = None


# Datos del cliente embebidos en la respuesta de pedido
class CustomerSummary(BaseModel):
    id: uuid.UUID
    name: str | None
    phone: str

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    order_number: int
    customer: CustomerSummary
    status: str
    payment_status: str
    origin: str
    delivery_type: str
    delivery_address: str | None
    total_amount: float
    credit_applied: float
    delivery_person_id: uuid.UUID | None
    internal_notes: str | None
    kitchen_notes: str | None
    delivery_notes: str | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []
    status_history: list[StatusHistoryResponse] = []
    incidents: list[IncidentResponse] = []

    model_config = {"from_attributes": True}


class OrderListItem(BaseModel):
    """Versión reducida para el listado del tablero."""
    id: uuid.UUID
    order_number: int
    customer: CustomerSummary
    status: str
    payment_status: str
    origin: str
    delivery_type: str
    total_amount: float
    delivery_person_id: uuid.UUID | None
    created_at: datetime
    # Resumen de productos (nombres)
    items_summary: list[str] = []

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    items: list[OrderListItem]
    total: int
    page: int
    page_size: int
