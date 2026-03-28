from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


WHATSAPP_STATUS_ENUM = sa.Enum(
    "connected", "disconnected", "scanning",
    name="whatsapp_status"
)


class WhatsappNumber(Base):
    """Número de WhatsApp vinculado a un comercio (sesión WPPConnect)."""

    __tablename__ = "whatsapp_numbers"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phone_number: Mapped[str] = mapped_column(sa.String(30), nullable=False, unique=True)
    # Nombre de sesión en WPPConnect
    session_name: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        WHATSAPP_STATUS_ENUM, default="disconnected", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    # Relaciones
    business: Mapped["Business"] = relationship("Business")  # noqa: F821
