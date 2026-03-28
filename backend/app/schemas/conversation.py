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


class ChatSessionDetail(BaseModel):
    """Sesión con datos del cliente y número de WhatsApp (para el panel HITL)."""

    id: int
    pizzeria_id: int
    customer_id: int
    customer_phone: str
    customer_name: str | None
    whatsapp_number_id: int
    whatsapp_session_name: str
    status: ChatSessionStatus
    messages: list[dict]          # lista de {role, content}
    inactive_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InactiveSessionRead(BaseModel):
    """Sesión inactiva devuelta por el endpoint de inactividad (usado por n8n)."""

    id: int
    pizzeria_id: int
    customer_id: int
    whatsapp_session_name: str
    status: ChatSessionStatus
    last_message_at: datetime | None
    active_order_id: int | None
    updated_at: datetime


class ChatSessionStatusUpdate(BaseModel):
    """Cambio de estado de una sesión (ej: derivar a humano)."""

    status: ChatSessionStatus


class SendMessageRequest(BaseModel):
    """Mensaje que el operador envía al cliente vía WPPConnect."""

    text: str
