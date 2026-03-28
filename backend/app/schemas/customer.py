from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CustomerCreate(BaseModel):
    """Datos para registrar un cliente en la pizzería."""

    phone: str
    name: str | None = None
    address: str | None = None
    notes: str | None = None


class CustomerRead(BaseModel):
    """Representación pública de un cliente."""

    id: int
    pizzeria_id: int
    phone: str
    name: str | None
    address: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    notes: str | None = None


class CustomerCreditRead(BaseModel):
    """Saldo a favor del cliente en la pizzería."""

    id: int
    pizzeria_id: int
    customer_id: int
    balance: float
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerCreditAdjust(BaseModel):
    """Ajuste de crédito (positivo = agregar, negativo = descontar)."""

    amount: float
    reason: str | None = None
