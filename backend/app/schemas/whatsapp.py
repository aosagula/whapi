from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.whatsapp import WhatsAppSessionStatus


class WhatsAppNumberCreate(BaseModel):
    """Datos para registrar un número de WhatsApp en una pizzería."""

    number: str
    session_name: str


class WhatsAppNumberRead(BaseModel):
    """Representación pública de un número de WhatsApp."""

    id: int
    pizzeria_id: int
    number: str
    session_name: str
    status: WhatsAppSessionStatus
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WhatsAppNumberUpdate(BaseModel):
    """Campos actualizables de un número de WhatsApp."""

    is_active: bool | None = None
    status: WhatsAppSessionStatus | None = None
