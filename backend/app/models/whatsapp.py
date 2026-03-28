from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Pizzeria
    from app.models.order import Order
    from app.models.conversation import ChatSession


class WhatsAppSessionStatus(str, enum.Enum):
    connected = "connected"
    disconnected = "disconnected"
    scanning_qr = "scanning_qr"


class WhatsAppNumber(Base, TimestampMixin):
    """Sesión WPPConnect vinculada a una pizzería."""

    __tablename__ = "whatsapp_numbers"

    id: Mapped[int] = mapped_column(primary_key=True)
    pizzeria_id: Mapped[int] = mapped_column(ForeignKey("pizzerias.id"), nullable=False)
    number: Mapped[str] = mapped_column(String(30), nullable=False)
    session_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[WhatsAppSessionStatus] = mapped_column(
        Enum(WhatsAppSessionStatus, name="whatsapp_session_status"),
        default=WhatsAppSessionStatus.disconnected,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    pizzeria: Mapped[Pizzeria] = relationship(back_populates="whatsapp_numbers")
    orders: Mapped[list[Order]] = relationship(back_populates="whatsapp_number")
    chat_sessions: Mapped[list[ChatSession]] = relationship(back_populates="whatsapp_number")
