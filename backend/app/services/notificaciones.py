"""Servicio de notificaciones automáticas al cliente vía WhatsApp."""
from __future__ import annotations

import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.whatsapp import WhatsappNumber

logger = logging.getLogger(__name__)

# ── Mensajes por evento ───────────────────────────────────────────────────────

def _mensaje_cambio_estado(
    order_number: int,
    new_status: str,
    delivery_type: str,
    total_amount: float,
    credit_applied: float = 0,
) -> str | None:
    """
    Devuelve el mensaje a enviar al cliente según el nuevo estado del pedido.
    Retorna None si el evento no tiene notificación asociada.
    """
    msgs: dict[str, str] = {
        "pending_preparation": f"Tu pedido #{order_number} fue recibido. ¡Estamos en eso!",
        "in_preparation":      f"¡Tu pedido #{order_number} está siendo preparado! 🍕",
        "delivered":           f"¡Tu pedido #{order_number} fue entregado! Gracias por elegirnos. 🎉",
        "with_incident":       (
            f"Tuvimos un inconveniente con tu pedido #{order_number}. "
            "Estamos resolviéndolo y te avisamos pronto."
        ),
    }

    # Mensajes según tipo de entrega para to_dispatch / in_delivery
    if new_status == "to_dispatch":
        if delivery_type == "delivery":
            return f"Tu pedido #{order_number} está listo y ya salió para entregarte. ¡En camino!"
        else:
            return f"Tu pedido #{order_number} está listo para retirar. ¡Te esperamos!"
    if new_status == "in_delivery":
        return f"Tu pedido #{order_number} está en camino. ¡Ya llega!"

    return msgs.get(new_status)


def _mensaje_cancelacion(
    order_number: int,
    payment_policy: str,
    total_amount: float,
) -> str:
    """Mensaje de notificación al cancelar un pedido."""
    if payment_policy == "credit":
        return (
            f"Tu pedido #{order_number} fue cancelado. "
            f"Tenés un crédito de ${total_amount:.0f} para tu próximo pedido."
        )
    return f"Tu pedido #{order_number} fue cancelado. No se realizó ningún cobro."


def _mensaje_pago_confirmado(order_number: int) -> str:
    return f"¡Recibimos tu pago! Tu pedido #{order_number} pasa a preparación."


def _mensaje_link_pago(order_number: int, link: str) -> str:
    return f"Podés pagar tu pedido #{order_number} acá: {link}"


# ── Envío via WPPConnect ──────────────────────────────────────────────────────

async def _obtener_numero_activo(
    business_id: uuid.UUID,
    db: AsyncSession,
) -> WhatsappNumber | None:
    """
    Obtiene el primer número activo y conectado del comercio.
    Retorna None si no hay ninguno disponible.
    """
    result = await db.execute(
        select(WhatsappNumber).where(
            WhatsappNumber.business_id == business_id,
            WhatsappNumber.is_active == True,       # noqa: E712
            WhatsappNumber.status == "connected",
        ).limit(1)
    )
    return result.scalar_one_or_none()


async def enviar_mensaje_whatsapp(
    phone: str,
    message: str,
    session_name: str,
    token: str | None = None,
) -> None:
    """
    Envía un mensaje de texto via WPPConnect.
    Si WPPConnect no está configurado o falla, loguea y continúa sin lanzar excepción.
    """
    if not settings.WPPCONNECT_HOST:
        logger.debug("WPPConnect no configurado — mensaje no enviado a %s: %s", phone, message)
        return

    # Priorizar token de sesión; fallback al secret key global
    bearer = token or settings.WPPCONNECT_SECRET_KEY
    headers: dict[str, str] = {}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"

    # WPPConnect espera el número en formato internacional sin '+'
    phone_normalized = phone.lstrip("+")
    host = settings.WPPCONNECT_HOST.rstrip("/")
    if not (host.startswith("http://") or host.startswith("https://")):
        host = f"http://{host}:{settings.WPPCONNECT_PORT}"
    url = f"{host}/api/{session_name}/send-message"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                url,
                json={"phone": f"{phone_normalized}@c.us", "message": message},
                headers=headers,
            )
        logger.info("Notificación enviada a %s", phone)
    except Exception as exc:  # noqa: BLE001
        # Las notificaciones nunca deben bloquear la operación principal
        logger.warning("No se pudo enviar notificación a %s: %s", phone, exc)


async def notificar_cambio_estado(
    business_id: uuid.UUID,
    order_number: int,
    new_status: str,
    delivery_type: str,
    customer_phone: str,
    total_amount: float,
    db: AsyncSession,
) -> None:
    """Envía la notificación automática al cliente cuando cambia el estado del pedido."""
    mensaje = _mensaje_cambio_estado(order_number, new_status, delivery_type, total_amount)
    if not mensaje:
        return

    numero = await _obtener_numero_activo(business_id, db)
    if not numero or not numero.session_name:
        return

    await enviar_mensaje_whatsapp(customer_phone, mensaje, numero.session_name, token=numero.wpp_token)


async def notificar_cancelacion(
    business_id: uuid.UUID,
    order_number: int,
    payment_policy: str,
    total_amount: float,
    customer_phone: str,
    db: AsyncSession,
) -> None:
    """Envía la notificación automática al cliente cuando se cancela un pedido."""
    mensaje = _mensaje_cancelacion(order_number, payment_policy, total_amount)
    numero = await _obtener_numero_activo(business_id, db)
    if not numero or not numero.session_name:
        return
    await enviar_mensaje_whatsapp(customer_phone, mensaje, numero.session_name, token=numero.wpp_token)


async def notificar_pago_confirmado(
    business_id: uuid.UUID,
    order_number: int,
    customer_phone: str,
    db: AsyncSession,
) -> None:
    """Notifica al cliente que su pago fue confirmado."""
    mensaje = _mensaje_pago_confirmado(order_number)
    numero = await _obtener_numero_activo(business_id, db)
    if not numero or not numero.session_name:
        return
    await enviar_mensaje_whatsapp(customer_phone, mensaje, numero.session_name, token=numero.wpp_token)


async def notificar_link_pago(
    business_id: uuid.UUID,
    order_number: int,
    link: str,
    customer_phone: str,
    db: AsyncSession,
) -> None:
    """Envía al cliente el link de pago de MercadoPago."""
    mensaje = _mensaje_link_pago(order_number, link)
    numero = await _obtener_numero_activo(business_id, db)
    if not numero or not numero.session_name:
        return
    await enviar_mensaje_whatsapp(customer_phone, mensaje, numero.session_name, token=numero.wpp_token)
