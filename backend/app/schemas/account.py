from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.account import PizzeriaRole


class AccountCreate(BaseModel):
    """Datos para registrar una nueva cuenta de dueño."""

    name: str
    email: EmailStr
    password: str
    phone: str | None = None


class AccountRead(BaseModel):
    """Representación pública de una cuenta."""

    id: int
    name: str
    email: EmailStr
    phone: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PizzeriaCreate(BaseModel):
    """Datos para crear una nueva pizzería."""

    name: str
    address: str | None = None
    city: str | None = None
    logo_url: str | None = None


class PizzeriaRead(BaseModel):
    """Representación pública de una pizzería."""

    id: int
    account_id: int
    name: str
    address: str | None
    city: str | None
    logo_url: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PizzeriaUpdate(BaseModel):
    """Campos actualizables de una pizzería."""

    name: str | None = None
    address: str | None = None
    city: str | None = None
    logo_url: str | None = None
    is_active: bool | None = None


class PanelUserCreate(BaseModel):
    """Datos para crear un usuario del panel (empleado)."""

    name: str
    email: EmailStr
    password: str


class PanelUserRead(BaseModel):
    """Representación pública de un usuario del panel."""

    id: int
    account_id: int
    name: str
    email: EmailStr
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserPizzeriaRoleCreate(BaseModel):
    """Asignación de rol a un usuario en una pizzería."""

    user_id: int
    pizzeria_id: int
    role: PizzeriaRole


class UserPizzeriaRoleRead(BaseModel):
    """Representación de la asignación de rol."""

    id: int
    user_id: int
    pizzeria_id: int
    role: PizzeriaRole

    model_config = {"from_attributes": True}
