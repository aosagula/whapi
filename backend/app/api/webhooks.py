from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select

from app.core.config import settings
from app.core.db import get_db
from app.models.conversation import ChatSession, ChatSessionStatus
from app.models.customer import Customer
from app.models.order import Order, OrderStatus, Payment, PaymentStatus
from app.models.whatsapp import WhatsAppNumber, WhatsAppSessionStatus
from app.schemas.webhooks import (
    MercadoPagoWebhookPayload,
    WPPConnectMessagePayload,
    WPPConnectStatusPayload,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# ---------------------------------------------------------------------------
# Guard de token compartido
# ---------------------------------------------------------------------------

def _verify_webhook_token(token: str = Query(..., alias="token")) -> None:
    """Valida que el token de la query string coincide con WEBHOOK_TOKEN."""
    if not settings.webhook_token or token != settings.webhook_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")


# ---------------------------------------------------------------------------
# Mapeo de estado WPPConnect → nuestro enum
# ---------------------------------------------------------------------------

_STATE_MAP: dict[str, WhatsAppSessionStatus] = {
    "CONNECTED": WhatsAppSessionStatus.connected,
    "qrReadSuccess": WhatsAppSessionStatus.scanning_qr,
    "qrReadFail": WhatsAppSessionStatus.disconnected,
    "DISCONNECTED": WhatsAppSessionStatus.disconnected,
    "UNPAIRED": WhatsAppSessionStatus.disconnected,
    "UNPAIRED_IDLE": WhatsAppSessionStatus.disconnected,
}


# ---------------------------------------------------------------------------
# WPPConnect — mensaje entrante
# ---------------------------------------------------------------------------

@router.post("/wppconnect", status_code=status.HTTP_200_OK)
async def wppconnect_message(
    payload: WPPConnectMessagePayload,
    _: None = Depends(_verify_webhook_token),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Recibe mensajes entrantes de WPPConnect.
    Rutea al tenant correcto por session_name → WhatsAppNumber → pizzeria_id.
    Crea cliente y sesión de chat si no existen.
    Respeta HITL: no procesa si la sesión está en 'transferred_human'.
    """
    if payload.event != "onmessage":
        return {"status": "ignored", "reason": f"event '{payload.event}' no procesado"}

    # Ignorar mensajes propios (eco)
    if payload.message_id and payload.message_id.fromMe:
        return {"status": "ignored", "reason": "mensaje propio"}

    # Ignorar mensajes de grupos
    if payload.is_group:
        return {"status": "ignored", "reason": "mensaje de grupo"}

    # --- Routing por session_name ---
    wa_result = await db.execute(
        select(WhatsAppNumber).where(
            WhatsAppNumber.session_name == payload.session,
            WhatsAppNumber.is_active.is_(True),
        )
    )
    wa_number = wa_result.scalar_one_or_none()
    if wa_number is None:
        logger.warning("Webhook WPPConnect: sesión '%s' no encontrada", payload.session)
        return {"status": "ignored", "reason": "sesión no registrada"}

    pizzeria_id = wa_number.pizzeria_id

    # Normalizar teléfono del remitente (quitar "@c.us" si viene con sufijo)
    raw_phone = payload.sender_phone or ""
    phone = raw_phone.split("@")[0] if "@" in raw_phone else raw_phone

    if not phone:
        logger.warning("Webhook WPPConnect: mensaje sin número de remitente")
        return {"status": "ignored", "reason": "remitente vacío"}

    # --- Obtener o crear Cliente ---
    cust_result = await db.execute(
        select(Customer).where(
            Customer.pizzeria_id == pizzeria_id,
            Customer.phone == phone,
        )
    )
    customer = cust_result.scalar_one_or_none()
    if customer is None:
        customer = Customer(pizzeria_id=pizzeria_id, phone=phone)
        db.add(customer)
        await db.flush()

    # --- Obtener o crear ChatSession ---
    sess_result = await db.execute(
        select(ChatSession).where(
            ChatSession.pizzeria_id == pizzeria_id,
            ChatSession.customer_id == customer.id,
            ChatSession.whatsapp_number_id == wa_number.id,
            ChatSession.status.notin_([ChatSessionStatus.closed]),
        )
    )
    session = sess_result.scalar_one_or_none()
    if session is None:
        session = ChatSession(
            pizzeria_id=pizzeria_id,
            customer_id=customer.id,
            whatsapp_number_id=wa_number.id,
            status=ChatSessionStatus.active,
            llm_context={"messages": []},
        )
        db.add(session)
        await db.flush()

    # --- HITL: si está derivada a humano, no procesar con LLM ---
    if session.status == ChatSessionStatus.transferred_human:
        logger.info(
            "Sesión %s en transferred_human — mensaje recibido pero no derivado al LLM",
            session.id,
        )
        _append_message(session, role="user", content=payload.body or "")
        session.inactive_at = datetime.now(timezone.utc)
        await db.commit()
        return {"status": "hitl", "session_id": session.id}

    # --- Registrar mensaje en contexto LLM ---
    _append_message(session, role="user", content=payload.body or "")
    session.inactive_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "status": "ok",
        "pizzeria_id": pizzeria_id,
        "customer_id": customer.id,
        "session_id": session.id,
    }


def _append_message(session: ChatSession, *, role: str, content: str) -> None:
    """Agrega un mensaje al historial llm_context de la sesión."""
    ctx = session.llm_context or {"messages": []}
    messages: list = ctx.get("messages", [])
    messages.append({"role": role, "content": content})
    session.llm_context = {"messages": messages}


# ---------------------------------------------------------------------------
# WPPConnect — cambio de estado de sesión
# ---------------------------------------------------------------------------

@router.post("/wppconnect/status", status_code=status.HTTP_200_OK)
async def wppconnect_status(
    payload: WPPConnectStatusPayload,
    _: None = Depends(_verify_webhook_token),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Recibe cambios de estado de sesión WPPConnect y actualiza WhatsAppNumber.status.
    """
    wa_result = await db.execute(
        select(WhatsAppNumber).where(
            WhatsAppNumber.session_name == payload.session,
        )
    )
    wa_number = wa_result.scalar_one_or_none()
    if wa_number is None:
        logger.warning("Webhook status: sesión '%s' no encontrada", payload.session)
        return {"status": "ignored", "reason": "sesión no registrada"}

    new_status = _STATE_MAP.get(payload.state, WhatsAppSessionStatus.disconnected)
    wa_number.status = new_status
    await db.commit()

    logger.info("Sesión '%s' → estado '%s'", payload.session, new_status.value)
    return {"status": "ok", "session": payload.session, "new_status": new_status.value}


# ---------------------------------------------------------------------------
# MercadoPago — notificación de pago
# ---------------------------------------------------------------------------

@router.post("/mercadopago", status_code=status.HTTP_200_OK)
async def mercadopago_webhook(
    request: Request,
    payload: MercadoPagoWebhookPayload,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Recibe notificaciones IPN de MercadoPago.
    Busca el pago por external_reference y actualiza su estado.
    Siempre devuelve 200 para evitar reintentos de MP.
    """
    # Verificación de firma x-signature (HMAC-SHA256)
    x_signature = request.headers.get("x-signature", "")
    x_request_id = request.headers.get("x-request-id", "")
    if not _verify_mp_signature(x_signature, x_request_id, payload.data.id):
        logger.warning("MercadoPago webhook: firma inválida para payment id %s", payload.data.id)
        # Devolvemos 200 igual — MP podría reenviar indefinidamente ante 4xx
        return {"status": "ignored", "reason": "firma inválida"}

    if payload.action not in ("payment.created", "payment.updated"):
        return {"status": "ignored", "reason": f"acción '{payload.action}' no procesada"}

    # Buscar pago por external_reference
    pay_result = await db.execute(
        select(Payment).where(Payment.external_reference == payload.data.id)
    )
    payment = pay_result.scalar_one_or_none()
    if payment is None:
        logger.info("MercadoPago webhook: pago '%s' no encontrado en DB", payload.data.id)
        return {"status": "ignored", "reason": "pago no registrado"}

    # En un flujo real consultaríamos la API de MP para confirmar el estado.
    # Por ahora marcamos como confirmado al recibir el webhook.
    payment.status = PaymentStatus.confirmed

    # Transicionar el pedido a pending_preparation si estaba en pendiente_pago
    order_result = await db.execute(
        select(Order).where(Order.id == payment.order_id)
    )
    order = order_result.scalar_one_or_none()
    if order and order.status == OrderStatus.pending_payment:
        order.status = OrderStatus.pending_preparation
        logger.info("Pedido %s → pending_preparation (pago MP confirmado)", order.id)

    await db.commit()

    logger.info("Pago %s confirmado vía MercadoPago webhook", payment.id)
    return {"status": "ok", "payment_id": payment.id}


def _verify_mp_signature(x_signature: str, x_request_id: str, data_id: str) -> bool:
    """
    Verifica la firma HMAC-SHA256 enviada por MercadoPago.
    Formato esperado de x-signature: 'ts=<timestamp>,v1=<hash>'
    Retorna True si la firma es válida o si no hay access_token configurado (entorno dev).
    """
    import hashlib
    import hmac

    if not settings.mercadopago_access_token:
        return True  # Entorno de desarrollo sin credenciales

    if not x_signature:
        return False

    parts = dict(part.split("=", 1) for part in x_signature.split(",") if "=" in part)
    ts = parts.get("ts", "")
    v1 = parts.get("v1", "")

    manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
    expected = hmac.new(
        settings.mercadopago_access_token.encode(),
        manifest.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, v1)
