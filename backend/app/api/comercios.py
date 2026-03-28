"""Endpoints de comercios del usuario autenticado."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.permisos import get_membresia, get_membresia_owner
from app.models.account import Business, User, UserBusiness
from app.schemas.comercio import (
    ComercioCreate,
    ComercioResponse,
    ComercioUpdate,
    MisComerciosResponse,
)
from app.services.comercios import crear_comercio, editar_comercio

router = APIRouter(prefix="/comercios", tags=["comercios"])


def _to_response(business: Business, role: str) -> ComercioResponse:
    return ComercioResponse(
        id=business.id,
        name=business.name,
        address=business.address,
        logo_url=business.logo_url,
        half_half_surcharge=business.half_half_surcharge,
        is_active=business.is_active,
        role=role,
    )


@router.get("/mis-comercios", response_model=MisComerciosResponse)
async def mis_comercios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MisComerciosResponse:
    """Retorna la lista de comercios a los que pertenece el usuario autenticado."""
    result = await db.execute(
        select(Business, UserBusiness.role)
        .join(UserBusiness, UserBusiness.business_id == Business.id)
        .where(
            UserBusiness.user_id == current_user.id,
            UserBusiness.is_active == True,  # noqa: E712
            Business.is_active == True,  # noqa: E712
        )
        .order_by(Business.name)
    )
    rows = result.all()
    return MisComerciosResponse(
        comercios=[_to_response(b, r) for b, r in rows]
    )


@router.post("", response_model=ComercioResponse, status_code=status.HTTP_201_CREATED)
async def crear(
    data: ComercioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComercioResponse:
    """Crea un nuevo comercio y asocia al usuario autenticado como owner."""
    business = await crear_comercio(data, current_user, db)
    return _to_response(business, "owner")


@router.get("/{comercio_id}", response_model=ComercioResponse)
async def detalle(
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
) -> ComercioResponse:
    """Retorna los datos del comercio (requiere ser miembro)."""
    business, membresia = ctx
    return _to_response(business, membresia.role)


@router.patch("/{comercio_id}", response_model=ComercioResponse)
async def editar(
    data: ComercioUpdate,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_owner),
    db: AsyncSession = Depends(get_db),
) -> ComercioResponse:
    """Edita los datos del comercio (solo owner)."""
    business, membresia = ctx
    business = await editar_comercio(business, data, db)
    return _to_response(business, membresia.role)
