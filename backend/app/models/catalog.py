from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.account import Pizzeria


class ProductCategory(str, enum.Enum):
    pizza = "pizza"
    empanada = "empanada"
    drink = "drink"


class ProductSize(str, enum.Enum):
    large = "large"
    small = "small"


class Product(Base, TimestampMixin, SoftDeleteMixin):
    """Inventario base de productos de una pizzería."""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("pizzeria_id", "code", name="uq_product_pizzeria_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pizzeria_id: Mapped[int] = mapped_column(ForeignKey("pizzerias.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    short_name: Mapped[str] = mapped_column(String(30), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[ProductCategory] = mapped_column(
        Enum(ProductCategory, name="product_category"), nullable=False
    )
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    pizzeria: Mapped[Pizzeria] = relationship(back_populates="products")
    catalog_items: Mapped[list[CatalogItem]] = relationship(back_populates="product")
    combo_items: Mapped[list[ComboItem]] = relationship(back_populates="product")


class CatalogItem(Base, TimestampMixin):
    """Precio y variante de un producto en el catálogo de la pizzería."""

    __tablename__ = "catalog_items"
    __table_args__ = (
        UniqueConstraint("pizzeria_id", "product_id", "size", name="uq_catalog_item_product_size"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pizzeria_id: Mapped[int] = mapped_column(ForeignKey("pizzerias.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    size: Mapped[ProductSize | None] = mapped_column(
        Enum(ProductSize, name="product_size"), nullable=True
    )
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    product: Mapped[Product] = relationship(back_populates="catalog_items")


class Combo(Base, TimestampMixin, SoftDeleteMixin):
    """Agrupación de productos con precio especial."""

    __tablename__ = "combos"
    __table_args__ = (
        UniqueConstraint("pizzeria_id", "code", name="uq_combo_pizzeria_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pizzeria_id: Mapped[int] = mapped_column(ForeignKey("pizzerias.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    short_name: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_customizable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    items: Mapped[list[ComboItem]] = relationship(back_populates="combo")


class ComboItem(Base):
    """Producto incluido en un combo."""

    __tablename__ = "combo_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    combo_id: Mapped[int] = mapped_column(ForeignKey("combos.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    combo: Mapped[Combo] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(back_populates="combo_items")


class PizzeriaConfig(Base):
    """Configuración operativa de una pizzería (una fila por tenant)."""

    __tablename__ = "pizzeria_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    pizzeria_id: Mapped[int] = mapped_column(
        ForeignKey("pizzerias.id"), unique=True, nullable=False
    )
    half_half_surcharge: Mapped[float] = mapped_column(
        Numeric(10, 2), default=0, nullable=False
    )
    delivery_surcharge: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    welcome_message: Mapped[str | None] = mapped_column(Text)
    closing_message: Mapped[str | None] = mapped_column(Text)
    opening_time: Mapped[str | None] = mapped_column(String(5))   # "HH:MM"
    closing_time: Mapped[str | None] = mapped_column(String(5))   # "HH:MM"
    bank_details: Mapped[str | None] = mapped_column(Text)

    pizzeria: Mapped[Pizzeria] = relationship(back_populates="config")
