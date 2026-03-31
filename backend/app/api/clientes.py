"""Endpoints de clientes: ABM, historial de pedidos y gestión de créditos."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import ROLES_GESTION, get_membresia
from app.models.account import Business, UserBusiness
from app.models.customer import Credit, Customer
from app.models.order import Order

router = APIRouter(tags=["clientes"])


# ── Schemas ───────────────────────────────────────────────────────────────────

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


class ClienteListResponse(BaseModel):
    items: list[ClienteResponse]
    total: int
    page: int
    page_size: int


class CreditoCreate(BaseModel):
    amount: float
    reason: str | None = None


class CreditoResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    amount: float
    reason: str | None
    order_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PedidoResumenResponse(BaseModel):
    id: uuid.UUID
    order_number: int
    status: str
    payment_status: str
    origin: str
    delivery_type: str
    total_amount: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_cliente_o_404(
    db: AsyncSession, business_id: uuid.UUID, cliente_id: uuid.UUID
) -> Customer:
    """Obtiene un cliente del comercio o lanza 404."""
    result = await db.execute(
        select(Customer).where(
            Customer.id == cliente_id,
            Customer.business_id == business_id,
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return customer


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/comercios/{comercio_id}/clientes",
    response_model=ClienteListResponse,
)
async def listar_clientes(
    comercio_id: uuid.UUID,
    q: str | None = Query(None, description="Búsqueda por nombre o teléfono"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> ClienteListResponse:
    """Lista clientes del comercio con paginación y búsqueda opcional."""
    business, _ = ctx

    base_filter = [Customer.business_id == business.id]
    if q:
        term = f"%{q}%"
        base_filter.append(
            or_(
                Customer.name.ilike(term),
                Customer.phone.ilike(term),
            )
        )

    total_result = await db.execute(
        select(func.count()).select_from(Customer).where(*base_filter)
    )
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    items_result = await db.execute(
        select(Customer)
        .where(*base_filter)
        .order_by(Customer.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = list(items_result.scalars().all())

    return ClienteListResponse(
        items=[ClienteResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


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
    customer = await _get_cliente_o_404(db, business.id, cliente_id)
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
    customer = await _get_cliente_o_404(db, business.id, cliente_id)

    if data.name is not None:
        customer.name = data.name
    if data.address is not None:
        customer.address = data.address
    if data.has_whatsapp is not None:
        customer.has_whatsapp = data.has_whatsapp

    await db.commit()
    await db.refresh(customer)
    return ClienteResponse.model_validate(customer)


@router.get(
    "/comercios/{comercio_id}/clientes/{cliente_id}/pedidos",
    response_model=list[PedidoResumenResponse],
)
async def listar_pedidos_del_cliente(
    comercio_id: uuid.UUID,
    cliente_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> list[PedidoResumenResponse]:
    """Historial de pedidos de un cliente en el comercio."""
    business, _ = ctx
    await _get_cliente_o_404(db, business.id, cliente_id)

    result = await db.execute(
        select(Order)
        .where(Order.customer_id == cliente_id, Order.business_id == business.id)
        .order_by(Order.created_at.desc())
    )
    orders = list(result.scalars().all())
    return [PedidoResumenResponse.model_validate(o) for o in orders]


@router.get(
    "/comercios/{comercio_id}/clientes/{cliente_id}/creditos",
    response_model=list[CreditoResponse],
)
async def listar_creditos_del_cliente(
    comercio_id: uuid.UUID,
    cliente_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> list[CreditoResponse]:
    """Historial de movimientos de crédito de un cliente."""
    business, _ = ctx
    await _get_cliente_o_404(db, business.id, cliente_id)

    result = await db.execute(
        select(Credit)
        .where(Credit.customer_id == cliente_id, Credit.business_id == business.id)
        .order_by(Credit.created_at.desc())
    )
    credits = list(result.scalars().all())
    return [CreditoResponse.model_validate(c) for c in credits]


@router.post(
    "/comercios/{comercio_id}/clientes/{cliente_id}/creditos",
    response_model=CreditoResponse,
    status_code=201,
)
async def ajustar_credito(
    comercio_id: uuid.UUID,
    cliente_id: uuid.UUID,
    data: CreditoCreate,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> CreditoResponse:
    """
    Registra un ajuste manual de crédito (positivo o negativo).
    Solo Admin y Dueño pueden hacerlo.
    """
    business, membresia = ctx
    if membresia.role not in ROLES_GESTION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol owner o admin para ajustar créditos",
        )

    customer = await _get_cliente_o_404(db, business.id, cliente_id)

    nuevo_saldo = float(customer.credit_balance) + data.amount
    if nuevo_saldo < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El crédito resultante no puede ser negativo",
        )

    # Registrar movimiento
    credit = Credit(
        business_id=business.id,
        customer_id=customer.id,
        amount=data.amount,
        reason=data.reason,
    )
    db.add(credit)

    # Actualizar saldo
    customer.credit_balance = nuevo_saldo
    await db.commit()
    await db.refresh(credit)
    return CreditoResponse.model_validate(credit)
