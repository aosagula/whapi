"""Lógica de negocio para registro y autenticación de usuarios."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, hash_password, verify_password
from app.models.account import User
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest


async def registrar_usuario(
    data: UserRegisterRequest,
    db: AsyncSession,
) -> tuple[User, TokenResponse]:
    """Registra un nuevo usuario y retorna el usuario creado junto con el token de acceso."""
    # Verificar que el email no esté en uso
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese email",
        )

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        phone=data.phone,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = TokenResponse(access_token=create_access_token(str(user.id)))
    return user, token


async def login_usuario(
    data: UserLoginRequest,
    db: AsyncSession,
) -> tuple[User, TokenResponse]:
    """Valida credenciales y retorna el token de acceso."""
    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email o contraseña incorrectos",
    )

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(data.password, user.password_hash):
        raise invalid_exc

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada",
        )

    token = TokenResponse(access_token=create_access_token(str(user.id)))
    return user, token
