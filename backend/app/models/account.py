from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _now() -> datetime:
    """Retorna el timestamp actual en UTC."""
    return datetime.now(timezone.utc)


class User(Base):
    """Usuario de la plataforma (dueño o empleado)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(sa.String(150), nullable=False)
    email: Mapped[str] = mapped_column(sa.String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(sa.String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    # Relaciones
    owned_businesses: Mapped[list[Business]] = relationship(
        "Business", back_populates="owner", foreign_keys="Business.owner_id"
    )
    business_memberships: Mapped[list[UserBusiness]] = relationship(
        "UserBusiness", back_populates="user"
    )


class Business(Base):
    """Comercio/pizzería dentro de la plataforma (tenant)."""

    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(150), nullable=False)
    address: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    # Recargo configurable para pizza mitad y mitad
    half_half_surcharge: Mapped[float] = mapped_column(
        sa.Numeric(10, 2), default=0, nullable=False
    )
    assistant_name: Mapped[str | None] = mapped_column(sa.String(150), nullable=True)
    assistant_system_prompt_master: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    assistant_system_prompt_default: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    # Relaciones
    owner: Mapped[User] = relationship("User", back_populates="owned_businesses", foreign_keys=[owner_id])
    memberships: Mapped[list[UserBusiness]] = relationship("UserBusiness", back_populates="business")


# Enum de roles dentro de un comercio
class UserRole(sa.Enum):
    """Roles posibles de un usuario dentro de un comercio."""
    pass


USER_ROLE_ENUM = sa.Enum(
    "owner", "admin", "cashier", "cook", "delivery",
    name="user_role"
)


class UserBusiness(Base):
    """Asociación entre un usuario y un comercio, con su rol en ese comercio."""

    __tablename__ = "user_business"
    __table_args__ = (
        sa.UniqueConstraint("user_id", "business_id", name="uq_user_business"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(USER_ROLE_ENUM, nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, nullable=False
    )

    # Relaciones
    user: Mapped[User] = relationship("User", back_populates="business_memberships")
    business: Mapped[Business] = relationship("Business", back_populates="memberships")
