"""Schemas Pydantic para catálogo: productos, precios y combos."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ── Productos ─────────────────────────────────────────────────────────────────

ProductCategory = Literal["pizza", "empanada", "drink"]


class ProductCreate(BaseModel):
    """Datos para crear un producto en el inventario."""

    code: str = Field(..., min_length=1, max_length=30)
    short_name: str = Field(..., min_length=1, max_length=30)
    full_name: str = Field(..., min_length=1, max_length=150)
    description: str | None = None
    category: ProductCategory
    is_available: bool = True


class ProductUpdate(BaseModel):
    """Campos editables de un producto (código no editable)."""

    short_name: str | None = Field(None, min_length=1, max_length=30)
    full_name: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = None
    is_available: bool | None = None


class CatalogItemData(BaseModel):
    """Precios embebidos de un item del catálogo."""

    id: uuid.UUID
    price_large: float | None = None
    price_small: float | None = None
    price_unit: float | None = None
    price_dozen: float | None = None
    is_available: bool

    model_config = {"from_attributes": True}


class ProductResponse(BaseModel):
    """Respuesta pública de un producto."""

    id: uuid.UUID
    business_id: uuid.UUID
    code: str
    short_name: str
    full_name: str
    description: str | None
    category: str
    is_available: bool
    created_at: datetime
    updated_at: datetime
    catalog_item: CatalogItemData | None = None

    model_config = {"from_attributes": True}


# ── Catálogo (precios) ────────────────────────────────────────────────────────

class CatalogItemCreate(BaseModel):
    """Datos para crear o actualizar los precios de un producto en el catálogo."""

    product_id: uuid.UUID
    # Precios según categoría del producto
    price_large: float | None = Field(None, ge=0)    # pizzas
    price_small: float | None = Field(None, ge=0)    # pizzas
    price_unit: float | None = Field(None, ge=0)     # empanadas y bebidas
    price_dozen: float | None = Field(None, ge=0)    # empanadas
    is_available: bool = True


class CatalogItemUpdate(BaseModel):
    """Campos actualizables de un item del catálogo."""

    price_large: float | None = Field(None, ge=0)
    price_small: float | None = Field(None, ge=0)
    price_unit: float | None = Field(None, ge=0)
    price_dozen: float | None = Field(None, ge=0)
    is_available: bool | None = None


class CatalogItemResponse(BaseModel):
    """Respuesta pública de un item del catálogo."""

    id: uuid.UUID
    business_id: uuid.UUID
    product_id: uuid.UUID
    price_large: float | None
    price_small: float | None
    price_unit: float | None
    price_dozen: float | None
    is_available: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Combos ────────────────────────────────────────────────────────────────────

class ComboItemCreate(BaseModel):
    """Un ítem dentro de un combo: producto fijo o slot abierto a elección del cliente."""

    # Producto fijo (is_open=False): product_id requerido
    product_id: uuid.UUID | None = None
    quantity: int = Field(1, ge=1)
    # Slot abierto (is_open=True): open_category requerido, product_id debe ser nulo
    is_open: bool = False
    open_category: Literal["pizza", "empanada", "drink"] | None = None

    @model_validator(mode="after")
    def validar_tipo_item(self) -> "ComboItemCreate":
        if self.is_open:
            if not self.open_category:
                raise ValueError("open_category es requerido cuando is_open=True")
            if self.product_id is not None:
                raise ValueError("product_id debe ser nulo cuando is_open=True")
        else:
            if self.product_id is None:
                raise ValueError("product_id es requerido cuando is_open=False")
        return self


class ComboItemResponse(BaseModel):
    """Respuesta de un ítem de combo."""

    id: uuid.UUID
    product_id: uuid.UUID | None
    quantity: int
    is_open: bool
    open_category: str | None
    product: ProductResponse | None = None

    model_config = {"from_attributes": True}


class ComboCreate(BaseModel):
    """Datos para crear un combo."""

    code: str = Field(..., min_length=1, max_length=30)
    short_name: str = Field(..., min_length=1, max_length=30)
    full_name: str = Field(..., min_length=1, max_length=150)
    description: str | None = None
    price: float = Field(..., ge=0)
    is_available: bool = True
    items: list[ComboItemCreate] = Field(default_factory=list)


class ComboUpdate(BaseModel):
    """Campos editables de un combo (código no editable)."""

    short_name: str | None = Field(None, min_length=1, max_length=30)
    full_name: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = None
    price: float | None = Field(None, ge=0)
    is_available: bool | None = None
    items: list[ComboItemCreate] | None = None


class ComboResponse(BaseModel):
    """Respuesta pública de un combo."""

    id: uuid.UUID
    business_id: uuid.UUID
    code: str
    short_name: str
    full_name: str
    description: str | None
    price: float
    is_available: bool
    created_at: datetime
    updated_at: datetime
    items: list[ComboItemResponse] = []

    model_config = {"from_attributes": True}


# ── Paginación ────────────────────────────────────────────────────────────────

class ProductListResponse(BaseModel):
    """Respuesta paginada de productos."""

    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
