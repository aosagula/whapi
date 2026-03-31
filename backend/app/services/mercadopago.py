"""Integración con MercadoPago — Checkout Pro."""
from __future__ import annotations

import logging
import uuid

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

MP_API_BASE = "https://api.mercadopago.com"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4()),
    }


async def crear_preferencia(
    order_id: uuid.UUID,
    order_number: int,
    total_amount: float,
    customer_phone: str,
    business_name: str,
    notification_url: str,
) -> dict:
    """
    Crea una preferencia de pago en MercadoPago.
    Retorna { init_point, sandbox_init_point, preference_id }.
    Si MP no está configurado, retorna un dict vacío con un link simulado.
    """
    if not settings.MERCADOPAGO_ACCESS_TOKEN:
        logger.debug("MercadoPago no configurado — preferencia simulada para pedido #%s", order_number)
        return {
            "preference_id": f"SIMULADO-{order_id}",
            "init_point": f"https://mp.example.com/pay/{order_id}",
            "sandbox_init_point": f"https://sandbox.mp.example.com/pay/{order_id}",
        }

    payload = {
        "items": [
            {
                "id": str(order_id),
                "title": f"Pedido #{order_number} — {business_name}",
                "quantity": 1,
                "unit_price": total_amount,
                "currency_id": "ARS",
            }
        ],
        "payer": {
            "phone": {"number": customer_phone},
        },
        "external_reference": str(order_id),
        "notification_url": notification_url,
        "back_urls": {
            "success": notification_url,
            "failure": notification_url,
            "pending": notification_url,
        },
        "auto_return": "approved",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{MP_API_BASE}/checkout/preferences",
                json=payload,
                headers=_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "preference_id": data["id"],
                "init_point": data["init_point"],
                "sandbox_init_point": data.get("sandbox_init_point", data["init_point"]),
            }
    except httpx.HTTPStatusError as exc:
        logger.error("Error MercadoPago al crear preferencia: %s", exc.response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error de MercadoPago: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo conectar con MercadoPago",
        ) from exc


async def verificar_pago(payment_id: str) -> dict:
    """
    Consulta el estado de un pago en MercadoPago.
    Retorna { status, external_reference, transaction_amount }.
    """
    if not settings.MERCADOPAGO_ACCESS_TOKEN:
        return {"status": "approved", "external_reference": payment_id, "transaction_amount": 0}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{MP_API_BASE}/v1/payments/{payment_id}",
                headers=_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": data.get("status"),
                "external_reference": data.get("external_reference"),
                "transaction_amount": data.get("transaction_amount", 0),
            }
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error de MercadoPago al verificar pago: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo conectar con MercadoPago",
        ) from exc
