"""Endpoints de autenticación: registro, login y perfil del usuario."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.db import get_db
from app.models.account import User
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth import login_usuario, registrar_usuario

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterResponse(UserResponse):
    """Respuesta del registro: incluye el token para auto-login."""

    token: TokenResponse


@router.post("/registro", response_model=RegisterResponse, status_code=201)
async def registro(
    data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """Registra un nuevo usuario. Retorna el usuario creado y un token de acceso."""
    user, token = await registrar_usuario(data, db)
    return RegisterResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        is_active=user.is_active,
        account_type=data.account_type,
        created_at=user.created_at,
        token=token,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Autentica un usuario y retorna el token JWT."""
    _, token = await login_usuario(data, db)
    return token


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Retorna el perfil del usuario autenticado."""
    return UserResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        phone=current_user.phone,
        is_active=current_user.is_active,
        account_type="owner",  # se refinará en Fase 2 con la lógica de membresías
        created_at=current_user.created_at,
    )
