from __future__ import annotations

from pydantic import BaseModel, EmailStr

from app.schemas.account import PizzeriaRead


class LoginRequest(BaseModel):
    """Credenciales de inicio de sesión."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Respuesta con el JWT emitido."""

    access_token: str
    token_type: str = "bearer"
    pizzeria_id: int | None = None
    role: str | None = None


class PanelLoginRequest(BaseModel):
    """Credenciales de login para empleados del panel."""

    email: EmailStr
    password: str
    pizzeria_id: int


class PizzeriaSelectorResponse(BaseModel):
    """Lista de pizzerías disponibles para seleccionar al iniciar sesión."""

    pizzerias: list[PizzeriaRead]
