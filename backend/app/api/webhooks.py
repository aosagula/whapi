"""
Endpoints de webhook — sin autenticación JWT.
- POST /webhooks/wppconnect: recibe mensajes entrantes de WPPConnect
- POST /webhooks/mercadopago: recibe notificaciones IPN de MercadoPago
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.models.conversation import ConversationSession, Message
from app.models.customer import Customer
from app.models.order import Order
from app.models.whatsapp import WhatsappNumber
from app.services.notificaciones import notificar_pago_confirmado
from app.services.mercadopago import verificar_pago
from app.services.whatsapp import _resolver_pn_lid_wpp

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_phone(value: str) -> str:
    """Normaliza un teléfono de WhatsApp al formato internacional sin prefijos de WA ni '+'."""
    return value.replace("@c.us", "").replace("@s.whatsapp.net", "").split("@")[0].lstrip("+").strip()


def _extract_contact_metadata(payload: dict) -> tuple[str | None, str | None, str | None, str | None, dict]:
    """Extrae metadatos de identidad del contacto desde el payload de WPPConnect."""
    data = payload.get("data", {}) if isinstance(payload.get("data"), dict) else {}
    sender = payload.get("sender", {}) if isinstance(payload.get("sender"), dict) else {}
    chat = payload.get("chat", {}) if isinstance(payload.get("chat"), dict) else {}
    contact = data.get("sender") if isinstance(data.get("sender"), dict) else {}
    source = sender or contact

    wa_id = (
        source.get("id")
        or payload.get("from")
        or data.get("from")
    )
    display_name = (
        source.get("formattedName")
        or source.get("name")
        or chat.get("formattedTitle")
        or chat.get("name")
    )
    profile_name = (
        source.get("pushname")
        or payload.get("notifyName")
        or data.get("notifyName")
        or source.get("shortName")
        or data.get("senderName")
    )
    business_name = source.get("verifiedName") or chat.get("formattedTitle")

    metadata = {
        "sender": source or None,
        "chat": chat or None,
        "notify_name": payload.get("notifyName") or data.get("notifyName"),
        "quoted_msg": data.get("quotedMsg") if isinstance(data.get("quotedMsg"), dict) else None,
    }
    return wa_id, display_name, profile_name, business_name, metadata


# ── Webhook WPPConnect ────────────────────────────────────────────────────────

@router.post("/wppconnect", status_code=status.HTTP_200_OK)
async def webhook_wppconnect(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Recibe eventos de WPPConnect.
    Identifica el tenant por el número destino (to), guarda el mensaje entrante
    en la sesión de conversación activa del cliente.
    Esta ruta no requiere JWT — WPPConnect la llama directamente.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload inválido")

    logger.info("Webhook WPPConnect recibido: %s", payload)

    event_type = payload.get("event") or payload.get("type", "")
    logger.info("Webhook WPPConnect event_type=%s", event_type)

    # Solo procesar mensajes entrantes
    if event_type not in ("onmessage", "message", "received"):
        logger.info("Webhook WPPConnect ignorado por tipo de evento: %s", event_type)
        return {"ok": True, "skipped": True}

    # Extraer campos del payload de WPPConnect
    # El payload varía según la versión; intentamos cubrir los formatos comunes
    to_number: str = (
        payload.get("to")
        or payload.get("session")
        or payload.get("data", {}).get("to", "")
    )
    from_number: str = (
        payload.get("from")
        or payload.get("data", {}).get("from", "")
        or payload.get("sender", {}).get("id", "")
    )
    content: str = (
        payload.get("body")
        or payload.get("data", {}).get("body", "")
        or payload.get("message", "")
        or ""
    )
    logger.info(
        "Webhook WPPConnect datos extraídos to=%s from=%s content=%s",
        to_number,
        from_number,
        content,
    )

    # Normalizar números (quitar @c.us, @s.whatsapp.net, etc.)
    to_clean = _normalize_phone(to_number)
    from_clean = _normalize_phone(from_number)
    logger.info("Webhook WPPConnect normalizado to=%s from=%s", to_clean, from_clean)

    if not to_clean or not from_clean:
        logger.debug("Webhook WPPConnect sin número origen/destino: %s", payload)
        return {"ok": True, "skipped": True}

    # Identificar el comercio por el número destino
    wa_result = await db.execute(
        select(WhatsappNumber).where(
            WhatsappNumber.phone_number.contains(to_clean),
            WhatsappNumber.is_active == True,  # noqa: E712
        ).limit(1)
    )
    wa_number = wa_result.scalar_one_or_none()
    if wa_number is None:
        logger.warning("Mensaje para número no registrado: %s", to_clean)
        return {"ok": True, "skipped": True}

    business_id = wa_number.business_id
    logger.info(
        "Webhook WPPConnect resuelto a comercio=%s whatsapp_number_id=%s",
        business_id,
        wa_number.id,
    )

    # Si el remitente llega como @lid, intentamos resolver el número real usando WPPConnect.
    raw_sender_id = from_number.split("@")[0].strip()
    resolved_phone = from_clean
    resolved_wa_id: str | None = None
    if "@lid" in from_number and wa_number.session_name:
        try:
            lid_resolution = await _resolver_pn_lid_wpp(
                wa_number.session_name,
                raw_sender_id,
                token=wa_number.wpp_token,
            )
            if isinstance(lid_resolution, tuple):
                lid_phone, lid_wa_id = lid_resolution
            else:
                lid_phone, lid_wa_id = lid_resolution, None
            if lid_phone:
                resolved_phone = lid_phone
            if lid_wa_id:
                resolved_wa_id = lid_wa_id
        except HTTPException:
            logger.warning("No se pudo resolver pn-lid %s; se usa el identificador recibido", raw_sender_id)

    logger.info(
        "Webhook WPPConnect teléfono resuelto from=%s resolved_phone=%s resolved_wa_id=%s",
        from_clean,
        resolved_phone,
        resolved_wa_id or "<vacío>",
    )

    # Buscar o crear cliente por su número de teléfono o por su identificador WA
    wa_id, display_name, profile_name, business_name, contact_metadata = _extract_contact_metadata(payload)
    effective_wa_id = resolved_wa_id or wa_id or from_number
    cust_result = await db.execute(
        select(Customer).where(
            Customer.business_id == business_id,
            or_(
                Customer.phone == resolved_phone,
                Customer.phone == from_clean,
                Customer.whatsapp_wa_id == effective_wa_id,
                Customer.whatsapp_wa_id == from_number,
            ),
        ).limit(1)
    )
    customer = cust_result.scalar_one_or_none()

    if customer is None:
        # Crear cliente anónimo para la sesión
        logger.info("Webhook WPPConnect creando cliente nuevo phone=%s", resolved_phone)
        customer = Customer(
            business_id=business_id,
            phone=resolved_phone,
            has_whatsapp=True,
            whatsapp_wa_id=effective_wa_id,
            whatsapp_display_name=display_name,
            whatsapp_profile_name=profile_name,
            whatsapp_business_name=business_name,
            whatsapp_metadata=contact_metadata,
        )
        db.add(customer)
        await db.flush()
    else:
        logger.info("Webhook WPPConnect reutilizando cliente id=%s name=%s", customer.id, customer.name)
        if resolved_phone and customer.phone != resolved_phone:
            customer.phone = resolved_phone
        customer.whatsapp_wa_id = effective_wa_id or customer.whatsapp_wa_id
        customer.whatsapp_display_name = display_name or customer.whatsapp_display_name
        customer.whatsapp_profile_name = profile_name or customer.whatsapp_profile_name
        customer.whatsapp_business_name = business_name or customer.whatsapp_business_name
        customer.whatsapp_metadata = contact_metadata

    # Buscar sesión activa (active_bot o waiting_operator) del cliente
    sess_result = await db.execute(
        select(ConversationSession)
        .where(
            ConversationSession.customer_id == customer.id,
            ConversationSession.business_id == business_id,
            ConversationSession.status.in_(["active_bot", "waiting_operator", "assigned_human"]),
        )
        .order_by(ConversationSession.created_at.desc())
        .limit(1)
    )
    session = sess_result.scalar_one_or_none()

    if session is None:
        # Crear nueva sesión
        logger.info("Webhook WPPConnect creando nueva sesión para cliente=%s", customer.id)
        session = ConversationSession(
            business_id=business_id,
            customer_id=customer.id,
            whatsapp_number_id=wa_number.id,
            status="active_bot",
        )
        db.add(session)
        await db.flush()
    else:
        logger.info(
            "Webhook WPPConnect reutilizando sesión id=%s status=%s",
            session.id,
            session.status,
        )

    # Guardar el mensaje entrante
    if content:
        logger.info("Webhook WPPConnect guardando mensaje inbound en sesión=%s", session.id)
        msg = Message(
            session_id=session.id,
            direction="inbound",
            content=content,
            external_message_id=str(
                payload.get("id")
                or payload.get("messageId")
                or payload.get("data", {}).get("id", "")
            ) or None,
            sender_phone=resolved_phone,
            sender_name=display_name or profile_name,
            raw_payload=payload,
        )
        db.add(msg)
        session.last_message_at = _now()
    else:
        logger.info("Webhook WPPConnect sin contenido; no se persiste mensaje")

    await db.commit()
    logger.info(
        "Mensaje entrante de %s para comercio %s guardado en sesión %s",
        resolved_phone, business_id, session.id,
    )
    return {"ok": True, "session_id": str(session.id)}


# ── Webhook MercadoPago ───────────────────────────────────────────────────────

@router.post("/mercadopago", status_code=status.HTTP_200_OK)
async def webhook_mercadopago(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Recibe notificaciones IPN/webhook de MercadoPago.
    Verifica el pago y actualiza el estado del pedido correspondiente.
    Esta ruta no requiere JWT — MercadoPago la llama directamente.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload inválido")

    # MercadoPago envía { type, data: { id } } o { action, data: { id } }
    notif_type = payload.get("type") or payload.get("action", "")
    payment_id = str(payload.get("data", {}).get("id", ""))

    if notif_type not in ("payment", "payment.created", "payment.updated") or not payment_id:
        # Otros tipos de notificación (merchant_order, etc.) — ignorar
        return {"ok": True, "skipped": True}

    # Verificar el pago con la API de MP
    pago = await verificar_pago(payment_id)

    if pago.get("status") != "approved":
        logger.info("Pago %s no aprobado (status: %s) — ignorado", payment_id, pago.get("status"))
        return {"ok": True, "skipped": True}

    # external_reference es el UUID del pedido
    external_ref = pago.get("external_reference", "")
    try:
        order_id = uuid.UUID(external_ref)
    except (ValueError, AttributeError):
        logger.warning("external_reference inválido: %s", external_ref)
        return {"ok": True, "skipped": True}

    # Actualizar el pedido
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.customer))
    )
    order = result.scalar_one_or_none()
    if order is None:
        logger.warning("Pedido %s no encontrado para pago %s", order_id, payment_id)
        return {"ok": True, "skipped": True}

    if order.payment_status == "paid":
        # Pago ya procesado — idempotencia
        return {"ok": True, "skipped": True}

    order.payment_status = "paid"

    # Si el pedido estaba en pending_preparation o esperando pago, avanzar a pending_preparation
    if order.status in ("in_progress", "pending_payment"):
        order.status = "pending_preparation"

    await db.commit()
    await db.refresh(order)

    # Notificar al cliente que el pago fue confirmado
    if order.customer:
        await notificar_pago_confirmado(
            business_id=order.business_id,
            order_number=order.order_number,
            customer_phone=order.customer.phone,
            db=db,
        )

    logger.info("Pago confirmado para pedido #%s (id: %s)", order.order_number, order_id)
    return {"ok": True, "order_id": str(order_id)}
