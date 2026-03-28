from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import ActivePizzeriaId, DBSession, OwnerOrAdminRequired
from app.models.conversation import ChatSession, ChatSessionStatus
from app.models.customer import Customer
from app.models.whatsapp import WhatsAppNumber
from app.schemas.conversation import (
    ChatSessionDetail,
    ChatSessionRead,
    ChatSessionStatusUpdate,
    SendMessageRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["conversaciones"])

# ---------------------------------------------------------------------------
# Transiciones de estado HITL permitidas
# ---------------------------------------------------------------------------

_VALID_HITL_TRANSITIONS: dict[ChatSessionStatus, set[ChatSessionStatus]] = {
    ChatSessionStatus.active: {
        ChatSessionStatus.transferred_human,
        ChatSessionStatus.closed,
    },
    ChatSessionStatus.waiting_human: {
        ChatSessionStatus.transferred_human,
        ChatSessionStatus.closed,
    },
    ChatSessionStatus.transferred_human: {
        ChatSessionStatus.active,
        ChatSessionStatus.closed,
    },
    ChatSessionStatus.closed: set(),
}

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _get_session(
    session_id: int, pizzeria_id: int, db: DBSession
) -> ChatSession:
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.pizzeria_id == pizzeria_id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesión no encontrada",
        )
    return session


def _build_detail(
    session: ChatSession,
    customer: Customer,
    wa_number: WhatsAppNumber,
) -> ChatSessionDetail:
    ctx = session.llm_context or {}
    messages = ctx.get("messages", [])
    return ChatSessionDetail(
        id=session.id,
        pizzeria_id=session.pizzeria_id,
        customer_id=session.customer_id,
        customer_phone=customer.phone,
        customer_name=customer.name,
        whatsapp_number_id=session.whatsapp_number_id,
        whatsapp_session_name=wa_number.session_name,
        status=session.status,
        messages=messages,
        inactive_at=session.inactive_at,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/pizzerias/{pizzeria_id}/conversaciones",
    response_model=list[ChatSessionDetail],
)
async def list_sessions(
    pizzeria_id: int,
    active_pid: ActivePizzeriaId,
    db: DBSession,
    session_status: ChatSessionStatus | None = Query(default=None, alias="status"),
) -> list[ChatSessionDetail]:
    """
    Lista sesiones de conversación de la pizzería.
    Sin filtro devuelve todas las no cerradas; con ?status= filtra por estado.
    """
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    stmt = select(ChatSession, Customer, WhatsAppNumber).join(
        Customer, Customer.id == ChatSession.customer_id
    ).join(
        WhatsAppNumber, WhatsAppNumber.id == ChatSession.whatsapp_number_id
    ).where(
        ChatSession.pizzeria_id == active_pid,
    )

    if session_status is not None:
        stmt = stmt.where(ChatSession.status == session_status)
    else:
        stmt = stmt.where(ChatSession.status != ChatSessionStatus.closed)

    stmt = stmt.order_by(ChatSession.updated_at.desc())
    result = await db.execute(stmt)

    return [
        _build_detail(sess, cust, wa)
        for sess, cust, wa in result.all()
    ]


@router.get(
    "/pizzerias/{pizzeria_id}/conversaciones/{session_id}",
    response_model=ChatSessionDetail,
)
async def get_session(
    pizzeria_id: int,
    session_id: int,
    active_pid: ActivePizzeriaId,
    db: DBSession,
) -> ChatSessionDetail:
    """Detalle de una sesión con historial de mensajes."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    session = await _get_session(session_id, active_pid, db)

    cust = await db.get(Customer, session.customer_id)
    wa = await db.get(WhatsAppNumber, session.whatsapp_number_id)

    return _build_detail(session, cust, wa)  # type: ignore[arg-type]


@router.patch(
    "/pizzerias/{pizzeria_id}/conversaciones/{session_id}/estado",
    response_model=ChatSessionDetail,
)
async def update_session_status(
    pizzeria_id: int,
    session_id: int,
    body: ChatSessionStatusUpdate,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> ChatSessionDetail:
    """
    Cambia el estado de la sesión.
    - active → transferred_human : operador toma la conversación (HITL ON)
    - transferred_human → active  : devuelve el control al bot (HITL OFF)
    - cualquier estado → closed   : cierra la sesión
    """
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    session = await _get_session(session_id, active_pid, db)

    allowed = _VALID_HITL_TRANSITIONS.get(session.status, set())
    if body.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Transición inválida: '{session.status.value}' → '{body.status.value}'. "
                f"Permitidas: {[s.value for s in allowed] or 'ninguna'}."
            ),
        )

    session.status = body.status
    await db.commit()
    await db.refresh(session)

    cust = await db.get(Customer, session.customer_id)
    wa = await db.get(WhatsAppNumber, session.whatsapp_number_id)
    return _build_detail(session, cust, wa)  # type: ignore[arg-type]


@router.post(
    "/pizzerias/{pizzeria_id}/conversaciones/{session_id}/mensajes",
    response_model=ChatSessionDetail,
)
async def send_message(
    pizzeria_id: int,
    session_id: int,
    body: SendMessageRequest,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> ChatSessionDetail:
    """
    Envía un mensaje al cliente vía WPPConnect y lo registra en el contexto.
    Solo disponible cuando la sesión está en estado 'transferred_human'.
    """
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    session = await _get_session(session_id, active_pid, db)

    if session.status != ChatSessionStatus.transferred_human:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solo se pueden enviar mensajes manuales en sesiones derivadas a humano.",
        )

    cust = await db.get(Customer, session.customer_id)
    wa = await db.get(WhatsAppNumber, session.whatsapp_number_id)

    if cust is None or wa is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Datos de sesión incompletos.",
        )

    # Enviar mensaje a través de WPPConnect
    await _wppconnect_send(
        session_name=wa.session_name,
        phone=cust.phone,
        text=body.text,
    )

    # Registrar en llm_context como mensaje del operador
    ctx = session.llm_context or {"messages": []}
    messages: list = ctx.get("messages", [])
    messages.append({"role": "operator", "content": body.text})
    session.llm_context = {"messages": messages}
    await db.commit()
    await db.refresh(session)

    return _build_detail(session, cust, wa)


# ---------------------------------------------------------------------------
# WPPConnect helper
# ---------------------------------------------------------------------------

async def _wppconnect_send(session_name: str, phone: str, text: str) -> None:
    """Llama a WPPConnect para enviar un mensaje de texto."""
    if not settings.wppconnect_host:
        logger.warning("WPPCONNECT_HOST no configurado; mensaje no enviado.")
        return

    base = f"http://{settings.wppconnect_host}:{settings.wppconnect_port}"
    url = f"{base}/api/{session_name}/send-message"
    headers = {"Authorization": f"Bearer {settings.wppconnect_secret_key}"}
    payload = {"phone": phone, "message": text, "isGroup": False}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Error al enviar mensaje por WPPConnect: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No se pudo enviar el mensaje: {exc}",
        )
