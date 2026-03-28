from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Pizzeria
    from app.models.customer import Customer
    from app.models.whatsapp import WhatsAppNumber


class ChatSessionStatus(str, enum.Enum):
    active = "active"
    waiting_human = "waiting_human"
    transferred_human = "transferred_human"
    closed = "closed"


class ChatSession(Base, TimestampMixin):
    """Estado de una conversación de WhatsApp con el chatbot."""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    pizzeria_id: Mapped[int] = mapped_column(ForeignKey("pizzerias.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    whatsapp_number_id: Mapped[int] = mapped_column(
        ForeignKey("whatsapp_numbers.id"), nullable=False
    )
    status: Mapped[ChatSessionStatus] = mapped_column(
        Enum(ChatSessionStatus, name="chat_session_status"),
        default=ChatSessionStatus.active,
        nullable=False,
    )
    llm_context: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Historial de mensajes para el LLM"
    )
    inactive_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pizzeria: Mapped[Pizzeria] = relationship(back_populates="chat_sessions")
    customer: Mapped[Customer] = relationship(back_populates="chat_sessions")
    whatsapp_number: Mapped[WhatsAppNumber] = relationship(back_populates="chat_sessions")
