"""Dependencias de autorización por rol dentro de un comercio."""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.account import Business, User, UserBusiness

# Roles con acceso de gestión (pueden administrar empleados y config)
ROLES_GESTION = {"owner", "admin"}


async def get_membresia(
    comercio_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[Business, UserBusiness]:
    """
    Verifica que el usuario autenticado sea miembro activo del comercio.
    Retorna (comercio, membresia). Lanza 404 si el comercio no existe, 403 si no es miembro.
    """
    # Verificar que el comercio existe
    result = await db.execute(
        select(Business).where(Business.id == comercio_id, Business.is_active == True)  # noqa: E712
    )
    business = result.scalar_one_or_none()
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comercio no encontrado")

    # Verificar membresía activa
    result = await db.execute(
        select(UserBusiness).where(
            UserBusiness.user_id == current_user.id,
            UserBusiness.business_id == comercio_id,
            UserBusiness.is_active == True,  # noqa: E712
        )
    )
    membresia = result.scalar_one_or_none()
    if membresia is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    return business, membresia


async def get_membresia_gestion(
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
) -> tuple[Business, UserBusiness]:
    """Igual que get_membresia pero además exige rol owner o admin."""
    business, membresia = ctx
    if membresia.role not in ROLES_GESTION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol owner o admin",
        )
    return business, membresia


async def get_membresia_owner(
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
) -> tuple[Business, UserBusiness]:
    """Igual que get_membresia pero además exige rol owner."""
    business, membresia = ctx
    if membresia.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol owner",
        )
    return business, membresia
