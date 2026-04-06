"""Endpoints internos para el orquestador n8n del chatbot.

Autenticación: header X-N8N-Api-Key validado contra N8N_API_KEY en .env.
Sin JWT de usuario — estos endpoints son consumidos exclusivamente por n8n.
Todo query filtra por business_id (multi-tenancy).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.db import get_db
from app.models.catalog import CatalogItem, Combo, ComboItem, Product
from app.models.conversation import ConversationSession, Message
from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatusHistory
from app.models.whatsapp import WhatsappNumber
from app.services.mercadopago import crear_preferencia
from app.services.notificaciones import enviar_mensaje_whatsapp

router = APIRouter(prefix="/n8n", tags=["n8n-interno"])


# ── Autenticación interna ─────────────────────────────────────────────────────

def _verificar_api_key(x_n8n_api_key: str = Header(..., alias="X-N8N-Api-Key")) -> None:
    """Valida la clave interna de n8n. Lanza 401 si no coincide."""
    if not settings.N8N_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="N8N_API_KEY no configurada en el servidor",
        )
    if x_n8n_api_key != settings.N8N_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida",
        )


ApiKeyDep = Depends(_verificar_api_key)


# ── Schemas de request/response ───────────────────────────────────────────────

class TenantInfo(BaseModel):
    """Información del comercio identificado por número de WhatsApp destino."""
    business_id: uuid.UUID
    business_name: str
    whatsapp_number_id: uuid.UUID
    session_name: str
    wpp_token: str | None


class CustomerInfo(BaseModel):
    customer_id: uuid.UUID
    phone: str
    name: str | None
    address: str | None
    credit_balance: float


class OrderItemInfo(BaseModel):
    item_id: uuid.UUID
    product_id: uuid.UUID | None
    combo_id: uuid.UUID | None
    product_name: str | None
    quantity: int
    unit_price: float
    variant: dict | None
    notes: str | None
    subtotal: float


class ActiveOrderInfo(BaseModel):
    order_id: uuid.UUID
    order_number: int
    status: str
    delivery_type: str
    delivery_address: str | None
    total_amount: float
    credit_applied: float
    items: list[OrderItemInfo]


class MessageInfo(BaseModel):
    direction: str
    content: str
    sent_at: datetime


class ChatbotContext(BaseModel):
    """Contexto completo que el orquestador necesita en cada turno."""
    business_id: uuid.UUID
    business_name: str
    session_id: uuid.UUID
    session_status: str
    customer: CustomerInfo
    active_order: ActiveOrderInfo | None
    recent_messages: list[MessageInfo]


class GuardarMensajeRequest(BaseModel):
    session_id: uuid.UUID
    direction: str = Field(..., pattern="^(inbound|outbound)$")
    content: str


class BuscarOCrearClienteRequest(BaseModel):
    phone: str
    name: str | None = None


class ActualizarClienteRequest(BaseModel):
    name: str | None = None
    address: str | None = None


class ProductoPrecioInfo(BaseModel):
    code: str
    full_name: str
    short_name: str
    category: str
    price_large: float | None
    price_small: float | None
    price_unit: float | None
    price_dozen: float | None


class ComboPrecioInfo(BaseModel):
    code: str
    full_name: str
    short_name: str
    price: float
    description: str | None
    items_descripcion: str


class CatalogoCompleto(BaseModel):
    productos: list[ProductoPrecioInfo]
    combos: list[ComboPrecioInfo]
    recargo_mitad_mitad: float


class CrearPedidoRequest(BaseModel):
    customer_id: uuid.UUID
    session_id: uuid.UUID
    delivery_type: str = Field(..., pattern="^(delivery|pickup)$")
    delivery_address: str | None = None


class AgregarItemRequest(BaseModel):
    product_id: uuid.UUID | None = None
    combo_id: uuid.UUID | None = None
    quantity: int = Field(1, ge=1)
    unit_price: float = Field(..., ge=0)
    variant: dict | None = None
    notes: str | None = None


class ConfirmarPedidoRequest(BaseModel):
    delivery_type: str | None = None
    delivery_address: str | None = None


class PagoRequest(BaseModel):
    method: str = Field(..., pattern="^(mercadopago|cash|transfer)$")
    credit_to_apply: float = Field(0, ge=0)


class PagoResponse(BaseModel):
    method: str
    payment_status: str
    mp_link: str | None = None
    datos_transferencia: str | None = None


class DerivarRequest(BaseModel):
    session_id: uuid.UUID
    motivo: str | None = None


class SesionInactiva(BaseModel):
    session_id: uuid.UUID
    business_id: uuid.UUID
    customer_phone: str
    customer_name: str | None
    order_id: uuid.UUID
    order_number: int
    last_message_at: datetime
    session_name: str
    wpp_token: str | None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _get_business_or_404(db: AsyncSession, business_id: uuid.UUID):
    """Obtiene el comercio o lanza 404."""
    from app.models.account import Business
    result = await db.execute(
        select(Business).where(Business.id == business_id)
    )
    business = result.scalar_one_or_none()
    if business is None:
        raise HTTPException(status_code=404, detail="Comercio no encontrado")
    return business


async def _siguiente_order_number(db: AsyncSession, business_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.max(Order.order_number)).where(Order.business_id == business_id)
    )
    return (result.scalar_one_or_none() or 0) + 1


async def _nombre_producto(db: AsyncSession, product_id: uuid.UUID | None, combo_id: uuid.UUID | None) -> str | None:
    if product_id:
        r = await db.execute(select(Product.full_name).where(Product.id == product_id))
        return r.scalar_one_or_none()
    if combo_id:
        r = await db.execute(select(Combo.full_name).where(Combo.id == combo_id))
        return r.scalar_one_or_none()
    return None


async def _order_to_info(db: AsyncSession, order: Order) -> ActiveOrderInfo:
    items_info: list[OrderItemInfo] = []
    for item in order.items:
        nombre = await _nombre_producto(db, item.product_id, item.combo_id)
        items_info.append(OrderItemInfo(
            item_id=item.id,
            product_id=item.product_id,
            combo_id=item.combo_id,
            product_name=nombre,
            quantity=item.quantity,
            unit_price=float(item.unit_price),
            variant=item.variant,
            notes=item.notes,
            subtotal=float(item.unit_price) * item.quantity,
        ))
    return ActiveOrderInfo(
        order_id=order.id,
        order_number=order.order_number,
        status=order.status,
        delivery_type=order.delivery_type,
        delivery_address=order.delivery_address,
        total_amount=float(order.total_amount),
        credit_applied=float(order.credit_applied),
        items=items_info,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/resolver-tenant",
    response_model=TenantInfo,
    dependencies=[ApiKeyDep],
)
async def resolver_tenant(
    numero: str = Query(..., description="Número de WhatsApp destino (formato internacional)"),
    db: AsyncSession = Depends(get_db),
) -> TenantInfo:
    """
    Identifica el comercio (tenant) por el número de WhatsApp destino del mensaje entrante.
    Normaliza el número eliminando '@c.us' y el prefijo '+' si los tiene.
    """
    numero_normalizado = numero.replace("@c.us", "").lstrip("+")
    result = await db.execute(
        select(WhatsappNumber).where(
            WhatsappNumber.phone_number == numero_normalizado,
            WhatsappNumber.is_active == True,  # noqa: E712
        )
    )
    wa_number = result.scalar_one_or_none()
    if wa_number is None:
        raise HTTPException(status_code=404, detail=f"Número {numero_normalizado} no registrado")

    business = await _get_business_or_404(db, wa_number.business_id)
    return TenantInfo(
        business_id=business.id,
        business_name=business.name,
        whatsapp_number_id=wa_number.id,
        session_name=wa_number.session_name or "",
        wpp_token=wa_number.wpp_token,
    )


@router.get(
    "/comercios/{business_id}/contexto",
    response_model=ChatbotContext,
    dependencies=[ApiKeyDep],
)
async def obtener_contexto(
    business_id: uuid.UUID,
    phone: str = Query(..., description="Número de teléfono del cliente (remitente)"),
    db: AsyncSession = Depends(get_db),
) -> ChatbotContext:
    """
    Carga el contexto completo para el turno del orquestador:
    cliente (creándolo si no existe), sesión activa (creándola si no existe),
    pedido en curso y últimos 20 mensajes.
    """
    business = await _get_business_or_404(db, business_id)

    # Normalizar número
    phone_normalizado = phone.replace("@c.us", "").lstrip("+")

    # Cliente: buscar o crear
    cust_result = await db.execute(
        select(Customer).where(
            Customer.business_id == business_id,
            Customer.phone == phone_normalizado,
        )
    )
    customer = cust_result.scalar_one_or_none()
    if customer is None:
        customer = Customer(
            business_id=business_id,
            phone=phone_normalizado,
        )
        db.add(customer)
        await db.flush()

    # Sesión activa: la más reciente que no esté cerrada
    sess_result = await db.execute(
        select(ConversationSession)
        .where(
            ConversationSession.business_id == business_id,
            ConversationSession.customer_id == customer.id,
            ConversationSession.status != "closed",
        )
        .order_by(ConversationSession.updated_at.desc())
        .limit(1)
    )
    session = sess_result.scalar_one_or_none()
    if session is None:
        session = ConversationSession(
            business_id=business_id,
            customer_id=customer.id,
            status="active_bot",
        )
        db.add(session)
        await db.flush()

    # Pedido en curso (status = in_progress)
    order_result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(
            Order.business_id == business_id,
            Order.customer_id == customer.id,
            Order.status == "in_progress",
        )
        .order_by(Order.created_at.desc())
        .limit(1)
    )
    order = order_result.scalar_one_or_none()

    # Últimos 20 mensajes de la sesión
    msg_result = await db.execute(
        select(Message)
        .where(Message.session_id == session.id)
        .order_by(Message.sent_at.desc())
        .limit(20)
    )
    mensajes = list(reversed(msg_result.scalars().all()))

    await db.commit()

    return ChatbotContext(
        business_id=business_id,
        business_name=business.name,
        session_id=session.id,
        session_status=session.status,
        customer=CustomerInfo(
            customer_id=customer.id,
            phone=customer.phone,
            name=customer.name,
            address=customer.address,
            credit_balance=float(customer.credit_balance),
        ),
        active_order=await _order_to_info(db, order) if order else None,
        recent_messages=[
            MessageInfo(direction=m.direction, content=m.content, sent_at=m.sent_at)
            for m in mensajes
        ],
    )


@router.post(
    "/comercios/{business_id}/mensajes",
    status_code=201,
    dependencies=[ApiKeyDep],
)
async def guardar_mensaje(
    business_id: uuid.UUID,
    data: GuardarMensajeRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Persiste un mensaje en el historial de la sesión y actualiza last_message_at."""
    sess_result = await db.execute(
        select(ConversationSession).where(
            ConversationSession.id == data.session_id,
            ConversationSession.business_id == business_id,
        )
    )
    session = sess_result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    msg = Message(
        session_id=session.id,
        direction=data.direction,
        content=data.content,
    )
    db.add(msg)

    if data.direction == "inbound":
        session.last_message_at = _now()

    await db.commit()
    return {"message_id": str(msg.id)}


@router.post(
    "/comercios/{business_id}/clientes/buscar-o-crear",
    response_model=CustomerInfo,
    dependencies=[ApiKeyDep],
)
async def buscar_o_crear_cliente(
    business_id: uuid.UUID,
    data: BuscarOCrearClienteRequest,
    db: AsyncSession = Depends(get_db),
) -> CustomerInfo:
    """Busca un cliente por teléfono; lo crea si no existe."""
    phone = data.phone.replace("@c.us", "").lstrip("+")
    result = await db.execute(
        select(Customer).where(
            Customer.business_id == business_id,
            Customer.phone == phone,
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        customer = Customer(business_id=business_id, phone=phone, name=data.name)
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
    return CustomerInfo(
        customer_id=customer.id,
        phone=customer.phone,
        name=customer.name,
        address=customer.address,
        credit_balance=float(customer.credit_balance),
    )


@router.patch(
    "/clientes/{cliente_id}",
    response_model=CustomerInfo,
    dependencies=[ApiKeyDep],
)
async def actualizar_cliente(
    cliente_id: uuid.UUID,
    data: ActualizarClienteRequest,
    db: AsyncSession = Depends(get_db),
) -> CustomerInfo:
    """Actualiza nombre y/o dirección del cliente."""
    result = await db.execute(select(Customer).where(Customer.id == cliente_id))
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if data.name is not None:
        customer.name = data.name
    if data.address is not None:
        customer.address = data.address

    await db.commit()
    await db.refresh(customer)
    return CustomerInfo(
        customer_id=customer.id,
        phone=customer.phone,
        name=customer.name,
        address=customer.address,
        credit_balance=float(customer.credit_balance),
    )


@router.get(
    "/comercios/{business_id}/catalogo",
    response_model=CatalogoCompleto,
    dependencies=[ApiKeyDep],
)
async def obtener_catalogo(
    business_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CatalogoCompleto:
    """Retorna el catálogo completo disponible del comercio: productos con precios y combos."""
    business = await _get_business_or_404(db, business_id)

    # Productos disponibles con precios
    prod_result = await db.execute(
        select(Product, CatalogItem)
        .join(CatalogItem, CatalogItem.product_id == Product.id, isouter=True)
        .where(
            Product.business_id == business_id,
            Product.is_available == True,  # noqa: E712
        )
        .order_by(Product.category, Product.full_name)
    )
    productos = [
        ProductoPrecioInfo(
            code=p.code,
            full_name=p.full_name,
            short_name=p.short_name,
            category=p.category,
            price_large=float(ci.price_large) if ci and ci.price_large is not None else None,
            price_small=float(ci.price_small) if ci and ci.price_small is not None else None,
            price_unit=float(ci.price_unit) if ci and ci.price_unit is not None else None,
            price_dozen=float(ci.price_dozen) if ci and ci.price_dozen is not None else None,
        )
        for p, ci in prod_result.all()
    ]

    # Combos disponibles con descripción de ítems
    combo_result = await db.execute(
        select(Combo)
        .options(selectinload(Combo.items).selectinload(ComboItem.product))
        .where(Combo.business_id == business_id, Combo.is_available == True)  # noqa: E712
        .order_by(Combo.full_name)
    )
    combos_raw = combo_result.scalars().all()
    combos = []
    for c in combos_raw:
        partes = []
        for ci in c.items:
            if ci.is_open:
                partes.append(f"{ci.quantity}x {ci.open_category} a elección")
            elif ci.product:
                partes.append(f"{ci.quantity}x {ci.product.short_name}")
        combos.append(ComboPrecioInfo(
            code=c.code,
            full_name=c.full_name,
            short_name=c.short_name,
            price=float(c.price),
            description=c.description,
            items_descripcion=", ".join(partes) if partes else "",
        ))

    return CatalogoCompleto(
        productos=productos,
        combos=combos,
        recargo_mitad_mitad=float(getattr(business, "half_half_surcharge", 0) or 0),
    )


@router.post(
    "/comercios/{business_id}/pedidos",
    response_model=ActiveOrderInfo,
    status_code=201,
    dependencies=[ApiKeyDep],
)
async def crear_pedido(
    business_id: uuid.UUID,
    data: CrearPedidoRequest,
    db: AsyncSession = Depends(get_db),
) -> ActiveOrderInfo:
    """Crea un pedido borrador (in_progress, origen whatsapp) para el cliente."""
    await _get_business_or_404(db, business_id)

    order_number = await _siguiente_order_number(db, business_id)
    order = Order(
        business_id=business_id,
        order_number=order_number,
        customer_id=data.customer_id,
        session_id=data.session_id,
        status="in_progress",
        payment_status="no_charge",
        origin="whatsapp",
        delivery_type=data.delivery_type,
        delivery_address=data.delivery_address,
        total_amount=0,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    # Cargar items (vacío al crear)
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    )
    order = result.scalar_one()
    return await _order_to_info(db, order)


@router.post(
    "/comercios/{business_id}/pedidos/{pedido_id}/items",
    response_model=ActiveOrderInfo,
    status_code=201,
    dependencies=[ApiKeyDep],
)
async def agregar_item(
    business_id: uuid.UUID,
    pedido_id: uuid.UUID,
    data: AgregarItemRequest,
    db: AsyncSession = Depends(get_db),
) -> ActiveOrderInfo:
    """Agrega un ítem al pedido en curso y recalcula el total."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == pedido_id, Order.business_id == business_id, Order.status == "in_progress")
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido en curso no encontrado")

    item = OrderItem(
        order_id=order.id,
        product_id=data.product_id,
        combo_id=data.combo_id,
        quantity=data.quantity,
        unit_price=data.unit_price,
        variant=data.variant,
        notes=data.notes,
    )
    db.add(item)
    await db.flush()

    # Recalcular total
    order.total_amount = sum(
        float(i.unit_price) * i.quantity for i in order.items
    ) + float(data.unit_price) * data.quantity

    await db.commit()

    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    )
    order = result.scalar_one()
    return await _order_to_info(db, order)


@router.delete(
    "/comercios/{business_id}/pedidos/{pedido_id}/items/{item_id}",
    response_model=ActiveOrderInfo,
    dependencies=[ApiKeyDep],
)
async def quitar_item(
    business_id: uuid.UUID,
    pedido_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ActiveOrderInfo:
    """Elimina un ítem del pedido en curso y recalcula el total."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == pedido_id, Order.business_id == business_id, Order.status == "in_progress")
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido en curso no encontrado")

    item_result = await db.execute(
        select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == pedido_id)
    )
    item = item_result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Ítem no encontrado")

    await db.delete(item)
    await db.flush()

    # Recalcular total sin el ítem eliminado
    items_restantes = [i for i in order.items if i.id != item_id]
    order.total_amount = sum(float(i.unit_price) * i.quantity for i in items_restantes)

    await db.commit()

    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    )
    order = result.scalar_one()
    return await _order_to_info(db, order)


@router.get(
    "/comercios/{business_id}/pedidos/{pedido_id}/resumen",
    response_model=ActiveOrderInfo,
    dependencies=[ApiKeyDep],
)
async def resumen_pedido(
    business_id: uuid.UUID,
    pedido_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ActiveOrderInfo:
    """Retorna el resumen del pedido con todos sus ítems."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == pedido_id, Order.business_id == business_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return await _order_to_info(db, order)


@router.post(
    "/comercios/{business_id}/pedidos/{pedido_id}/confirmar",
    response_model=ActiveOrderInfo,
    dependencies=[ApiKeyDep],
)
async def confirmar_pedido(
    business_id: uuid.UUID,
    pedido_id: uuid.UUID,
    data: ConfirmarPedidoRequest,
    db: AsyncSession = Depends(get_db),
) -> ActiveOrderInfo:
    """
    Confirma el pedido (in_progress → pending_payment).
    Actualiza delivery_type y delivery_address si se proveen.
    """
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == pedido_id, Order.business_id == business_id, Order.status == "in_progress")
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido en curso no encontrado")

    if not order.items:
        raise HTTPException(status_code=400, detail="El pedido no tiene ítems")

    if data.delivery_type:
        order.delivery_type = data.delivery_type
    if data.delivery_address is not None:
        order.delivery_address = data.delivery_address

    prev_status = order.status
    order.status = "pending_payment"

    history = OrderStatusHistory(
        order_id=order.id,
        previous_status=prev_status,
        new_status="pending_payment",
        note="Confirmado por el cliente vía chatbot",
    )
    db.add(history)
    await db.commit()

    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    )
    order = result.scalar_one()
    return await _order_to_info(db, order)


@router.post(
    "/comercios/{business_id}/pedidos/{pedido_id}/pago",
    response_model=PagoResponse,
    dependencies=[ApiKeyDep],
)
async def registrar_pago(
    business_id: uuid.UUID,
    pedido_id: uuid.UUID,
    data: PagoRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PagoResponse:
    """
    Registra el método de pago elegido por el cliente.
    - mercadopago: genera preferencia y devuelve el link.
    - cash: pasa directamente a pending_preparation.
    - transfer: queda en pending_payment, cajero confirma.
    """
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == pedido_id, Order.business_id == business_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if order.status not in ("pending_payment", "in_progress"):
        raise HTTPException(status_code=400, detail="El pedido no acepta pago en este estado")

    # Aplicar crédito si corresponde
    if data.credit_to_apply > 0:
        cust_result = await db.execute(select(Customer).where(Customer.id == order.customer_id))  # type: ignore[arg-type]
        customer = cust_result.scalar_one_or_none()
        if customer and customer.credit_balance >= data.credit_to_apply:
            credito = min(data.credit_to_apply, float(order.total_amount))
            order.credit_applied = credito
            customer.credit_balance = float(customer.credit_balance) - credito

    mp_link: str | None = None
    datos_transferencia: str | None = None

    if data.method == "mercadopago":
        cust_r = await db.execute(select(Customer).where(Customer.id == order.customer_id))  # type: ignore[arg-type]
        customer = cust_r.scalar_one_or_none()
        base_url = str(request.base_url).rstrip("/")
        from app.models.account import Business
        biz_r = await db.execute(select(Business).where(Business.id == business_id))
        business = biz_r.scalar_one()
        pref = await crear_preferencia(
            order_id=order.id,
            order_number=order.order_number,
            total_amount=float(order.total_amount) - float(order.credit_applied),
            customer_phone=customer.phone if customer else "",
            business_name=business.name,
            notification_url=f"{base_url}/webhooks/mercadopago",
        )
        mp_link = pref["init_point"]
        order.payment_status = "pending_payment"

    elif data.method == "cash":
        order.payment_status = "cash_on_delivery"
        prev = order.status
        order.status = "pending_preparation"
        db.add(OrderStatusHistory(
            order_id=order.id,
            previous_status=prev,
            new_status="pending_preparation",
            note="Pago en efectivo confirmado por chatbot",
        ))

    elif data.method == "transfer":
        order.payment_status = "pending_payment"
        # El cajero envía los datos bancarios desde el panel o están configurados en n8n
        datos_transferencia = None

    await db.commit()

    return PagoResponse(
        method=data.method,
        payment_status=order.payment_status,
        mp_link=mp_link,
        datos_transferencia=datos_transferencia,
    )


@router.post(
    "/conversaciones/{session_id}/derivar",
    dependencies=[ApiKeyDep],
)
async def derivar_a_humano(
    session_id: uuid.UUID,
    data: DerivarRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Cambia el estado de la sesión a waiting_operator y suspende el bot.
    El orquestador debe llamar esto cuando detecta que el cliente necesita atención humana.
    """
    result = await db.execute(
        select(ConversationSession).where(ConversationSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    session.status = "waiting_operator"
    await db.commit()
    return {"status": "waiting_operator", "session_id": str(session_id)}


@router.get(
    "/sesiones/inactivas",
    response_model=list[SesionInactiva],
    dependencies=[ApiKeyDep],
)
async def sesiones_inactivas(
    minutos: int = Query(10, ge=1, le=60),
    db: AsyncSession = Depends(get_db),
) -> list[SesionInactiva]:
    """
    Retorna sesiones en estado active_bot con pedido en curso (in_progress)
    cuyo último mensaje fue hace más de `minutos` minutos.
    Usado por el timer de inactividad de n8n.
    """
    from datetime import timedelta
    umbral = _now() - timedelta(minutes=minutos)

    sess_result = await db.execute(
        select(ConversationSession).where(
            ConversationSession.status == "active_bot",
            ConversationSession.last_message_at <= umbral,
            ConversationSession.last_message_at.isnot(None),
        )
    )
    sessions = sess_result.scalars().all()

    inactivas: list[SesionInactiva] = []
    for s in sessions:
        # Verificar que tenga un pedido en curso
        order_result = await db.execute(
            select(Order).where(
                Order.business_id == s.business_id,
                Order.customer_id == s.customer_id,
                Order.status == "in_progress",
            ).limit(1)
        )
        order = order_result.scalar_one_or_none()
        if order is None:
            continue

        cust_result = await db.execute(select(Customer).where(Customer.id == s.customer_id))
        customer = cust_result.scalar_one_or_none()
        if customer is None:
            continue

        # Obtener número de WA activo del comercio para enviar el mensaje
        wa_result = await db.execute(
            select(WhatsappNumber).where(
                WhatsappNumber.business_id == s.business_id,
                WhatsappNumber.is_active == True,  # noqa: E712
                WhatsappNumber.status == "connected",
            ).limit(1)
        )
        wa_number = wa_result.scalar_one_or_none()
        if wa_number is None:
            continue

        inactivas.append(SesionInactiva(
            session_id=s.id,
            business_id=s.business_id,
            customer_phone=customer.phone,
            customer_name=customer.name,
            order_id=order.id,
            order_number=order.order_number,
            last_message_at=s.last_message_at,
            session_name=wa_number.session_name or "",
            wpp_token=wa_number.wpp_token,
        ))

    return inactivas
