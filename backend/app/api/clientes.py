"""Endpoints de clientes (ABM completo en Fase 7; búsqueda y alta para Fase 6)."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import get_membresia
from app.models.account import Business, UserBusiness
from app.models.customer import Customer

router = APIRouter(tags=["clientes"])


class ClienteCreate(BaseModel):
    phone: str
    name: str | None = None
    address: str | None = None
    has_whatsapp: bool = True


class ClienteUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    has_whatsapp: bool | None = None


class ClienteResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    phone: str
    name: str | None
    address: str | None
    has_whatsapp: bool
    credit_balance: float
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get(
    "/comercios/{comercio_id}/clientes/buscar",
    response_model=ClienteResponse,
)
async def buscar_cliente_por_telefono(
    comercio_id: uuid.UUID,
    phone: str = Query(..., description="Número de teléfono a buscar"),
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> ClienteResponse:
    """Busca un cliente por número de teléfono dentro del comercio."""
    business, _ = ctx
    result = await db.execute(
        select(Customer).where(
            Customer.business_id == business.id,
            Customer.phone == phone,
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return ClienteResponse.model_validate(customer)


@router.post(
    "/comercios/{comercio_id}/clientes",
    response_model=ClienteResponse,
    status_code=201,
)
async def crear_cliente(
    comercio_id: uuid.UUID,
    data: ClienteCreate,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> ClienteResponse:
    """Crea un cliente en el comercio. Falla si el teléfono ya existe."""
    business, _ = ctx
    existing = await db.execute(
        select(Customer).where(
            Customer.business_id == business.id,
            Customer.phone == data.phone,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un cliente con ese teléfono en este comercio",
        )
    customer = Customer(
        business_id=business.id,
        phone=data.phone,
        name=data.name,
        address=data.address,
        has_whatsapp=data.has_whatsapp,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return ClienteResponse.model_validate(customer)


@router.get(
    "/comercios/{comercio_id}/clientes/{cliente_id}",
    response_model=ClienteResponse,
)
async def obtener_cliente(
    comercio_id: uuid.UUID,
    cliente_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> ClienteResponse:
    """Obtiene un cliente por ID."""
    business, _ = ctx
    result = await db.execute(
        select(Customer).where(
            Customer.id == cliente_id,
            Customer.business_id == business.id,
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return ClienteResponse.model_validate(customer)


@router.patch(
    "/comercios/{comercio_id}/clientes/{cliente_id}",
    response_model=ClienteResponse,
)
async def actualizar_cliente(
    comercio_id: uuid.UUID,
    cliente_id: uuid.UUID,
    data: ClienteUpdate,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> ClienteResponse:
    """Actualiza nombre, dirección o flag de WhatsApp del cliente."""
    business, _ = ctx
    result = await db.execute(
        select(Customer).where(
            Customer.id == cliente_id,
            Customer.business_id == business.id,
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")

    if data.name is not None:
        customer.name = data.name
    if data.address is not None:
        customer.address = data.address
    if data.has_whatsapp is not None:
        customer.has_whatsapp = data.has_whatsapp

    await db.commit()
    await db.refresh(customer)
    return ClienteResponse.model_validate(customer)
