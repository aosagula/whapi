"""Endpoints de conversaciones activas (HITL — Fase 8)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.permisos import get_membresia
from app.models.account import Business, User, UserBusiness
from app.models.conversation import ConversationSession, Message
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.whatsapp import WhatsappNumber
from app.services.notificaciones import enviar_mensaje_whatsapp

router = APIRouter(tags=["conversaciones"])

# Roles que pueden atender derivaciones
ROLES_HITL = {"owner", "admin", "cashier"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class ClienteResumen(BaseModel):
    id: uuid.UUID
    name: str | None
    phone: str
    address: str | None
    credit_balance: float

    model_config = {"from_attributes": True}


class ItemResumen(BaseModel):
    display_name: str | None
    quantity: int
    unit_price: float

    model_config = {"from_attributes": True}


class PedidoCursoResumen(BaseModel):
    id: uuid.UUID
    order_number: int
    status: str
    delivery_type: str
    delivery_address: str | None
    total_amount: float
    items: list[ItemResumen] = []

    model_config = {"from_attributes": True}


class SesionListItem(BaseModel):
    id: uuid.UUID
    status: str
    customer: ClienteResumen
    assigned_operator_id: uuid.UUID | None
    assigned_operator_name: str | None
    pedido_en_curso: PedidoCursoResumen | None
    created_at: datetime
    last_message_at: datetime | None
    # Tiempo de espera en segundos desde que se solicitó derivación
    wait_seconds: int

    model_config = {"from_attributes": True}


class MensajeResponse(BaseModel):
    id: uuid.UUID
    direction: str
    content: str
    sent_at: datetime

    model_config = {"from_attributes": True}


class SesionDetalleResponse(BaseModel):
    id: uuid.UUID
    status: str
    customer: ClienteResumen
    assigned_operator_id: uuid.UUID | None
    assigned_operator_name: str | None
    pedido_en_curso: PedidoCursoResumen | None
    messages: list[MensajeResponse] = []
    created_at: datetime
    last_message_at: datetime | None

    model_config = {"from_attributes": True}


class MensajeCreate(BaseModel):
    content: str


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_sesion_o_404(
    db: AsyncSession, business_id: uuid.UUID, session_id: uuid.UUID
) -> ConversationSession:
    result = await db.execute(
        select(ConversationSession).where(
            ConversationSession.id == session_id,
            ConversationSession.business_id == business_id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada")
    return session


async def _cargar_pedido_en_curso(
    db: AsyncSession, session_id: uuid.UUID, business_id: uuid.UUID
) -> PedidoCursoResumen | None:
    """Obtiene el pedido activo de una sesión (si existe)."""
    result = await db.execute(
        select(Order).where(
            Order.session_id == session_id,
            Order.business_id == business_id,
            Order.status.notin_(["delivered", "cancelled", "discarded"]),
        ).order_by(Order.created_at.desc()).limit(1)
    )
    order = result.scalar_one_or_none()
    if order is None:
        return None

    # Cargar ítems
    items_result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order.id)
    )
    items = list(items_result.scalars().all())

    item_resumenes = [
        ItemResumen(
            display_name=_item_display_name(item),
            quantity=item.quantity,
            unit_price=float(item.unit_price),
        )
        for item in items
    ]

    return PedidoCursoResumen(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        delivery_type=order.delivery_type,
        delivery_address=order.delivery_address,
        total_amount=float(order.total_amount),
        items=item_resumenes,
    )


def _item_display_name(item: OrderItem) -> str | None:
    """Nombre descriptivo del ítem (usa el variant JSON si existe)."""
    if item.variant and isinstance(item.variant, dict):
        return item.variant.get("display_name") or item.variant.get("name")
    return None


async def _cargar_sesion_list_item(
    db: AsyncSession,
    session: ConversationSession,
    now: datetime,
) -> SesionListItem:
    """Construye el DTO de lista para una sesión."""
    # Cliente
    customer_result = await db.execute(
        select(Customer).where(Customer.id == session.customer_id)
    )
    customer = customer_result.scalar_one()

    # Operador asignado
    operator_name: str | None = None
    if session.assigned_operator_id:
        op_result = await db.execute(
            select(User).where(User.id == session.assigned_operator_id)
        )
        op = op_result.scalar_one_or_none()
        operator_name = op.name if op else None

    pedido = await _cargar_pedido_en_curso(db, session.id, session.business_id)

    wait_seconds = int((now - session.updated_at.replace(tzinfo=timezone.utc)).total_seconds())
    wait_seconds = max(0, wait_seconds)

    return SesionListItem(
        id=session.id,
        status=session.status,
        customer=ClienteResumen.model_validate(customer),
        assigned_operator_id=session.assigned_operator_id,
        assigned_operator_name=operator_name,
        pedido_en_curso=pedido,
        created_at=session.created_at,
        last_message_at=session.last_message_at,
        wait_seconds=wait_seconds,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/comercios/{comercio_id}/conversaciones",
    response_model=list[SesionListItem],
)
async def listar_conversaciones_activas(
    comercio_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> list[SesionListItem]:
    """Lista chats de WhatsApp del comercio con su estado actual."""
    business, membresia = ctx

    if membresia.role not in ROLES_HITL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol cajero, admin u owner para ver conversaciones",
        )

    result = await db.execute(
        select(ConversationSession).where(
            ConversationSession.business_id == business.id,
            ConversationSession.whatsapp_number_id.isnot(None),
        ).order_by(
            func.coalesce(ConversationSession.last_message_at, ConversationSession.updated_at).desc()
        )
    )
    sessions = list(result.scalars().all())

    now = datetime.now(timezone.utc)
    items = []
    for s in sessions:
        items.append(await _cargar_sesion_list_item(db, s, now))
    return items


@router.get(
    "/comercios/{comercio_id}/conversaciones/{session_id}",
    response_model=SesionDetalleResponse,
)
async def obtener_conversacion(
    comercio_id: uuid.UUID,
    session_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> SesionDetalleResponse:
    """Detalle de una sesión: mensajes, cliente y pedido en curso."""
    business, membresia = ctx

    if membresia.role not in ROLES_HITL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado",
        )

    session = await _get_sesion_o_404(db, business.id, session_id)

    # Cliente
    customer_result = await db.execute(
        select(Customer).where(Customer.id == session.customer_id)
    )
    customer = customer_result.scalar_one()

    # Operador asignado
    operator_name: str | None = None
    if session.assigned_operator_id:
        op_result = await db.execute(
            select(User).where(User.id == session.assigned_operator_id)
        )
        op = op_result.scalar_one_or_none()
        operator_name = op.name if op else None

    # Mensajes
    msgs_result = await db.execute(
        select(Message).where(Message.session_id == session.id).order_by(Message.sent_at.asc())
    )
    messages = list(msgs_result.scalars().all())

    pedido = await _cargar_pedido_en_curso(db, session.id, business.id)

    return SesionDetalleResponse(
        id=session.id,
        status=session.status,
        customer=ClienteResumen.model_validate(customer),
        assigned_operator_id=session.assigned_operator_id,
        assigned_operator_name=operator_name,
        pedido_en_curso=pedido,
        messages=[MensajeResponse.model_validate(m) for m in messages],
        created_at=session.created_at,
        last_message_at=session.last_message_at,
    )


@router.post(
    "/comercios/{comercio_id}/conversaciones/{session_id}/atender",
    response_model=SesionDetalleResponse,
)
async def atender_conversacion(
    comercio_id: uuid.UUID,
    session_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SesionDetalleResponse:
    """
    El operador toma el control de una sesión en espera.
    Transición: waiting_operator → assigned_human.
    """
    business, membresia = ctx

    if membresia.role not in ROLES_HITL:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    session = await _get_sesion_o_404(db, business.id, session_id)

    if session.status != "waiting_operator":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La sesión está en estado '{session.status}', no se puede tomar",
        )

    session.status = "assigned_human"
    session.assigned_operator_id = current_user.id
    await db.commit()
    await db.refresh(session)

    # Recargar para la respuesta
    return await obtener_conversacion(comercio_id, session_id, ctx, db)


@router.post(
    "/comercios/{comercio_id}/conversaciones/{session_id}/mensaje",
    response_model=MensajeResponse,
    status_code=201,
)
async def enviar_mensaje(
    comercio_id: uuid.UUID,
    session_id: uuid.UUID,
    data: MensajeCreate,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> MensajeResponse:
    """
    El operador envía un mensaje al cliente.
    Se guarda como outbound en la DB. El dispatch real vía WPPConnect se implementa en Fase 10.
    Solo disponible cuando la sesión está en assigned_human.
    """
    business, membresia = ctx

    if membresia.role not in ROLES_HITL:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    if not data.content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El mensaje no puede estar vacío",
        )

    session = await _get_sesion_o_404(db, business.id, session_id)

    if session.status != "assigned_human":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede enviar mensajes cuando la sesión está derivada a un humano",
        )

    message = Message(
        session_id=session.id,
        direction="outbound",
        content=data.content.strip(),
    )
    db.add(message)

    customer_result = await db.execute(
        select(Customer).where(Customer.id == session.customer_id)
    )
    customer = customer_result.scalar_one()

    if session.whatsapp_number_id:
        numero_result = await db.execute(
            select(WhatsappNumber).where(
                WhatsappNumber.id == session.whatsapp_number_id,
                WhatsappNumber.business_id == business.id,
            )
        )
        numero = numero_result.scalar_one_or_none()
        if numero and numero.session_name:
            await enviar_mensaje_whatsapp(
                customer.phone,
                data.content.strip(),
                numero.session_name,
                token=numero.wpp_token,
            )

    # Actualizar last_message_at de la sesión
    session.last_message_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(message)

    return MensajeResponse.model_validate(message)


@router.post(
    "/comercios/{comercio_id}/conversaciones/{session_id}/devolver-al-bot",
    response_model=SesionDetalleResponse,
)
async def devolver_al_bot(
    comercio_id: uuid.UUID,
    session_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> SesionDetalleResponse:
    """
    Devuelve el control al LLM.
    Transición: assigned_human → active_bot.
    """
    business, membresia = ctx

    if membresia.role not in ROLES_HITL:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    session = await _get_sesion_o_404(db, business.id, session_id)

    if session.status != "assigned_human":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La sesión está en estado '{session.status}', no se puede devolver al bot",
        )

    session.status = "active_bot"
    session.assigned_operator_id = None
    await db.commit()
    await db.refresh(session)

    return await obtener_conversacion(comercio_id, session_id, ctx, db)


@router.post(
    "/comercios/{comercio_id}/conversaciones/{session_id}/cerrar",
    response_model=SesionDetalleResponse,
)
async def cerrar_sin_pedido(
    comercio_id: uuid.UUID,
    session_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> SesionDetalleResponse:
    """
    Cierra la sesión sin concretar pedido. Descarta el pedido en curso si existe.
    Transición: assigned_human → closed.
    """
    business, membresia = ctx

    if membresia.role not in ROLES_HITL:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    session = await _get_sesion_o_404(db, business.id, session_id)

    if session.status != "assigned_human":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La sesión está en estado '{session.status}', no se puede cerrar",
        )

    # Descartar pedido en curso si existe
    order_result = await db.execute(
        select(Order).where(
            Order.session_id == session.id,
            Order.business_id == business.id,
            Order.status.notin_(["delivered", "cancelled", "discarded"]),
        ).order_by(Order.created_at.desc()).limit(1)
    )
    order = order_result.scalar_one_or_none()
    if order:
        order.status = "discarded"

    session.status = "closed"
    await db.commit()
    await db.refresh(session)

    return await obtener_conversacion(comercio_id, session_id, ctx, db)
