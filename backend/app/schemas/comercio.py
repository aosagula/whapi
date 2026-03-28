"""Schemas Pydantic para comercios y empleados."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

RolComercio = Literal["owner", "admin", "cashier", "cook", "delivery"]


# ── Comercio ───────────────────────────────────────────────────────────────────

class ComercioCreate(BaseModel):
    """Datos para crear un nuevo comercio."""
    name: str
    address: str | None = None
    logo_url: str | None = None
    half_half_surcharge: Decimal = Decimal("0")


class ComercioUpdate(BaseModel):
    """Campos editables de un comercio (todos opcionales)."""
    name: str | None = None
    address: str | None = None
    logo_url: str | None = None
    half_half_surcharge: Decimal | None = None


class ComercioResponse(BaseModel):
    """Datos de un comercio para mostrar al usuario."""
    id: uuid.UUID
    name: str
    address: str | None
    logo_url: str | None
    half_half_surcharge: Decimal
    is_active: bool
    role: str  # rol del usuario autenticado en este comercio

    model_config = {"from_attributes": True}


class MisComerciosResponse(BaseModel):
    """Lista de comercios del usuario autenticado."""
    comercios: list[ComercioResponse]


# ── Empleados ──────────────────────────────────────────────────────────────────

class EmpleadoResponse(BaseModel):
    """Datos de un miembro del comercio."""
    user_id: uuid.UUID
    name: str
    email: str
    phone: str | None
    role: RolComercio
    is_active: bool
    joined_at: datetime

    model_config = {"from_attributes": True}


class EmpleadoAsociarRequest(BaseModel):
    """Petición para asociar un usuario existente a un comercio."""
    email: str
    role: RolComercio


class EmpleadoCambiarRolRequest(BaseModel):
    """Petición para cambiar el rol de un empleado."""
    role: RolComercio
