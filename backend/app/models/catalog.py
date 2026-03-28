from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


PRODUCT_CATEGORY_ENUM = sa.Enum(
    "pizza", "empanada", "drink",
    name="product_category"
)


class Product(Base):
    """Producto del inventario base del comercio."""

    __tablename__ = "products"
    __table_args__ = (
        # El código es único dentro de cada comercio
        sa.UniqueConstraint("business_id", "code", name="uq_product_code_per_business"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Código alfanumérico corto, inmutable una vez creado (ej: PIZ-MOZ)
    code: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    short_name: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    full_name: Mapped[str] = mapped_column(sa.String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    category: Mapped[str] = mapped_column(PRODUCT_CATEGORY_ENUM, nullable=False)
    # Soft delete: se desactiva si tiene pedidos históricos, nunca se elimina
    is_available: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    # Relaciones
    business: Mapped["Business"] = relationship("Business")  # noqa: F821
    catalog_item: Mapped[CatalogItem | None] = relationship(
        "CatalogItem", back_populates="product", uselist=False
    )
    combo_items: Mapped[list[ComboItem]] = relationship("ComboItem", back_populates="product")


class CatalogItem(Base):
    """Precios del producto en el catálogo del comercio."""

    __tablename__ = "catalog_items"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # Precios para pizzas (grande / chica)
    price_large: Mapped[float | None] = mapped_column(sa.Numeric(10, 2), nullable=True)
    price_small: Mapped[float | None] = mapped_column(sa.Numeric(10, 2), nullable=True)
    # Precio para empanadas y bebidas
    price_unit: Mapped[float | None] = mapped_column(sa.Numeric(10, 2), nullable=True)
    # Precio por docena (empanadas)
    price_dozen: Mapped[float | None] = mapped_column(sa.Numeric(10, 2), nullable=True)
    is_available: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    # Relaciones
    product: Mapped[Product] = relationship("Product", back_populates="catalog_item")


class Combo(Base):
    """Combo con precio especial que agrupa varios productos."""

    __tablename__ = "combos"
    __table_args__ = (
        sa.UniqueConstraint("business_id", "code", name="uq_combo_code_per_business"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    short_name: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    full_name: Mapped[str] = mapped_column(sa.String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    price: Mapped[float] = mapped_column(sa.Numeric(10, 2), nullable=False)
    is_available: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    # Relaciones
    items: Mapped[list[ComboItem]] = relationship("ComboItem", back_populates="combo")


class ComboItem(Base):
    """Producto individual que forma parte de un combo."""

    __tablename__ = "combo_items"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    combo_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("combos.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)

    # Relaciones
    combo: Mapped[Combo] = relationship("Combo", back_populates="items")
    product: Mapped[Product] = relationship("Product", back_populates="combo_items")
