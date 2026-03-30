"""Endpoints del tablero de pedidos."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import get_membresia
from app.models.account import Business, UserBusiness
from app.schemas.pedidos import (
    IncidentCreate,
    OrderAssignDelivery,
    OrderCancel,
    OrderCreate,
    OrderListResponse,
    OrderResponse,
    OrderUpdateNotes,
    OrderUpdatePayment,
    OrderUpdateStatus,
)
from app.services import pedidos as svc

router = APIRouter(tags=["pedidos"])


@router.get(
    "/comercios/{comercio_id}/pedidos",
    response_model=OrderListResponse,
)
async def listar_pedidos(
    comercio_id: uuid.UUID,
    status: str | None = Query(None),
    payment_status: str | None = Query(None),
    delivery_person_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> OrderListResponse:
    """Lista pedidos del comercio con filtros y paginación."""
    business, membresia = ctx
    items, total = await svc.listar_pedidos(
        db=db,
        business_id=business.id,
        status_filter=status,
        payment_status_filter=payment_status,
        delivery_person_filter=delivery_person_id,
        page=page,
        page_size=page_size,
        user_role=membresia.role,
        user_id=membresia.user_id,
    )
    return OrderListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/comercios/{comercio_id}/pedidos/{pedido_id}",
    response_model=OrderResponse,
)
async def obtener_pedido(
    comercio_id: uuid.UUID,
    pedido_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Detalle completo de un pedido: items, historial, incidencias."""
    business, _ = ctx
    return await svc.obtener_pedido(db, business.id, pedido_id)


@router.post(
    "/comercios/{comercio_id}/pedidos",
    response_model=OrderResponse,
    status_code=201,
)
async def crear_pedido(
    comercio_id: uuid.UUID,
    data: OrderCreate,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Crea un pedido manual (cajero u operador)."""
    business, membresia = ctx
    return await svc.crear_pedido(db, business.id, data, created_by_id=membresia.user_id)


@router.patch(
    "/comercios/{comercio_id}/pedidos/{pedido_id}/estado",
    response_model=OrderResponse,
)
async def cambiar_estado(
    comercio_id: uuid.UUID,
    pedido_id: uuid.UUID,
    data: OrderUpdateStatus,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Avanza o cambia el estado del pedido según las transiciones permitidas."""
    business, membresia = ctx
    return await svc.cambiar_estado(
        db, business.id, pedido_id, data,
        user_id=membresia.user_id, user_role=membresia.role,
    )


@router.patch(
    "/comercios/{comercio_id}/pedidos/{pedido_id}/pago",
    response_model=OrderResponse,
)
async def marcar_pago(
    comercio_id: uuid.UUID,
    pedido_id: uuid.UUID,
    data: OrderUpdatePayment,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Actualiza el estado de pago del pedido."""
    business, membresia = ctx
    return await svc.marcar_pagado(db, business.id, pedido_id, data, user_role=membresia.role)


@router.patch(
    "/comercios/{comercio_id}/pedidos/{pedido_id}/repartidor",
    response_model=OrderResponse,
)
async def asignar_repartidor(
    comercio_id: uuid.UUID,
    pedido_id: uuid.UUID,
    data: OrderAssignDelivery,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Asigna o desasigna el repartidor de un pedido."""
    business, membresia = ctx
    return await svc.asignar_repartidor(
        db, business.id, pedido_id, data, user_role=membresia.role
    )


@router.patch(
    "/comercios/{comercio_id}/pedidos/{pedido_id}/notas",
    response_model=OrderResponse,
)
async def actualizar_notas(
    comercio_id: uuid.UUID,
    pedido_id: uuid.UUID,
    data: OrderUpdateNotes,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Actualiza las notas internas del pedido."""
    business, _ = ctx
    return await svc.actualizar_notas(db, business.id, pedido_id, data)


@router.post(
    "/comercios/{comercio_id}/pedidos/{pedido_id}/cancelar",
    response_model=OrderResponse,
)
async def cancelar_pedido(
    comercio_id: uuid.UUID,
    pedido_id: uuid.UUID,
    data: OrderCancel,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Cancela un pedido con la política de pago correspondiente."""
    business, membresia = ctx
    return await svc.cancelar_pedido(
        db, business.id, pedido_id, data,
        user_id=membresia.user_id, user_role=membresia.role,
    )


@router.post(
    "/comercios/{comercio_id}/pedidos/{pedido_id}/incidencia",
    response_model=OrderResponse,
    status_code=201,
)
async def reportar_incidencia(
    comercio_id: uuid.UUID,
    pedido_id: uuid.UUID,
    data: IncidentCreate,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Reporta una incidencia en el pedido."""
    business, membresia = ctx
    return await svc.reportar_incidencia(
        db, business.id, pedido_id, data,
        user_id=membresia.user_id, user_role=membresia.role,
    )


@router.post(
    "/comercios/{comercio_id}/pedidos/{pedido_id}/incidencias/{incidencia_id}/redespacho",
    response_model=OrderResponse,
)
async def resolver_redespacho(
    comercio_id: uuid.UUID,
    pedido_id: uuid.UUID,
    incidencia_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Resuelve una incidencia con re-despacho."""
    business, membresia = ctx
    return await svc.resolver_redespacho(
        db, business.id, pedido_id, incidencia_id,
        user_id=membresia.user_id, user_role=membresia.role,
    )
