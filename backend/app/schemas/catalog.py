from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.catalog import ProductCategory, ProductSize


class ProductCreate(BaseModel):
    """Datos para crear un producto en el catálogo."""

    code: str
    short_name: str
    full_name: str
    description: str | None = None
    category: ProductCategory
    is_available: bool = True


class ProductRead(BaseModel):
    """Representación pública de un producto."""

    id: int
    pizzeria_id: int
    code: str
    short_name: str
    full_name: str
    description: str | None
    category: ProductCategory
    is_available: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductUpdate(BaseModel):
    """Campos actualizables de un producto. El código es inmutable."""

    short_name: str | None = None
    full_name: str | None = None
    description: str | None = None
    is_available: bool | None = None


class CatalogItemCreate(BaseModel):
    """Datos para agregar un precio/variante al catálogo."""

    product_id: int
    size: ProductSize | None = None
    price: float
    is_active: bool = True


class CatalogItemRead(BaseModel):
    """Representación pública de un ítem del catálogo."""

    id: int
    pizzeria_id: int
    product_id: int
    size: ProductSize | None
    price: float
    is_active: bool

    model_config = {"from_attributes": True}


class CatalogItemUpdate(BaseModel):
    price: float | None = None
    is_active: bool | None = None


class ComboCreate(BaseModel):
    """Datos para crear un combo."""

    name: str
    description: str | None = None
    price: float
    is_available: bool = True


class ComboRead(BaseModel):
    """Representación pública de un combo."""

    id: int
    pizzeria_id: int
    name: str
    description: str | None
    price: float
    is_available: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ComboUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    is_available: bool | None = None


class PizzeriaConfigRead(BaseModel):
    """Configuración operativa de la pizzería."""

    id: int
    pizzeria_id: int
    half_half_surcharge: float
    welcome_message: str | None
    opening_time: str | None
    closing_time: str | None

    model_config = {"from_attributes": True}


class PizzeriaConfigUpdate(BaseModel):
    half_half_surcharge: float | None = None
    welcome_message: str | None = None
    opening_time: str | None = None
    closing_time: str | None = None
