"""Schemas Pydantic para números de WhatsApp."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

WhatsappStatus = str  # "connected" | "disconnected" | "scanning"


class WhatsappNumberCreate(BaseModel):
    """Datos para agregar un número de WhatsApp al comercio."""
    phone_number: str
    label: str | None = None


class WhatsappNumberUpdate(BaseModel):
    """Campos editables de un número (todos opcionales)."""
    label: str | None = None
    is_active: bool | None = None


class WhatsappNumberResponse(BaseModel):
    """Datos de un número de WhatsApp para mostrar al usuario."""
    id: uuid.UUID
    business_id: uuid.UUID
    phone_number: str
    label: str | None
    session_name: str | None
    status: WhatsappStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WhatsappQRResponse(BaseModel):
    """Respuesta del QR de escaneo de una sesión WPPConnect."""
    session_name: str
    # QR en formato base64 (data:image/png;base64,...)
    qr_code: str | None
    status: WhatsappStatus
