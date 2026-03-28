"""Schemas Pydantic para comercios."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ComercioResponse(BaseModel):
    """Datos de un comercio para mostrar al usuario."""

    id: uuid.UUID
    name: str
    address: str | None
    logo_url: str | None
    is_active: bool
    role: str  # rol del usuario en este comercio

    model_config = {"from_attributes": True}


class MisComerciosResponse(BaseModel):
    """Lista de comercios del usuario autenticado."""

    comercios: list[ComercioResponse]
