"""Schemas Pydantic para autenticación y usuario."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, field_validator


class UserRegisterRequest(BaseModel):
    """Datos necesarios para registrar un nuevo usuario."""

    name: str
    email: EmailStr
    password: str
    phone: str | None = None
    # Tipo de cuenta: distingue entre dueño de comercio y empleado/colaborador
    account_type: Literal["owner", "employee"]

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


class UserLoginRequest(BaseModel):
    """Credenciales de login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Respuesta del endpoint de login."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Datos públicos del usuario."""

    id: uuid.UUID
    name: str
    email: str
    phone: str | None
    is_active: bool
    account_type: Literal["owner", "employee"]
    created_at: datetime

    model_config = {"from_attributes": True}
