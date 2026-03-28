from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


SESSION_STATUS_ENUM = sa.Enum(
    "active_bot",        # el LLM está atendiendo normalmente
    "waiting_operator",  # derivación solicitada, sin operador asignado aún
    "assigned_human",    # operador tomó el control, LLM suspendido
    "closed",            # sesión finalizada
    name="session_status"
)

MESSAGE_DIRECTION_ENUM = sa.Enum(
    "inbound",   # mensaje del cliente
    "outbound",  # mensaje enviado al cliente (bot u operador)
    name="message_direction"
)


class ConversationSession(Base):
    """Sesión de conversación de un cliente con el chatbot o un operador humano."""

    __tablename__ = "conversation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    whatsapp_number_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("whatsapp_numbers.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        SESSION_STATUS_ENUM, default="active_bot", nullable=False
    )
    # Operador asignado cuando la sesión está en estado assigned_human
    assigned_operator_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Timestamp del último mensaje recibido (usado por el timer de inactividad)
    last_message_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    # Relaciones
    messages: Mapped[list[Message]] = relationship(
        "Message", back_populates="session", order_by="Message.sent_at"
    )


class Message(Base):
    """Mensaje individual dentro de una sesión de conversación."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    direction: Mapped[str] = mapped_column(MESSAGE_DIRECTION_ENUM, nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, default=_now
    )

    # Relaciones
    session: Mapped[ConversationSession] = relationship(
        "ConversationSession", back_populates="messages"
    )
