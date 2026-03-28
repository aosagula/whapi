from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.conversation import ChatSessionStatus


class ChatSessionRead(BaseModel):
    """Representación pública de una sesión de conversación."""

    id: int
    pizzeria_id: int
    customer_id: int
    whatsapp_number_id: int
    status: ChatSessionStatus
    llm_context: dict | None
    inactive_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionStatusUpdate(BaseModel):
    """Cambio de estado de una sesión (ej: derivar a humano)."""

    status: ChatSessionStatus
