"""Tests de webhooks (WPPConnect y MercadoPago)."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "http://test"


def _email(tag: str) -> str:
    return f"{tag}_{uuid.uuid4().hex[:8]}@test.com"


async def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE)


async def _registrar(client: AsyncClient, tag: str) -> dict:
    resp = await client.post(
        "/auth/registro",
        json={"name": f"User {tag}", "email": _email(tag), "password": "password123", "account_type": "owner"},
    )
    assert resp.status_code == 201
    return resp.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _setup_comercio(client: AsyncClient, tag: str) -> tuple[dict, str]:
    """Registra usuario, crea comercio y devuelve (comercio, token)."""
    user = await _registrar(client, tag)
    token = user["token"]["access_token"]
    resp = await client.post("/comercios", json={"name": f"Comercio {tag}"}, headers=_auth(token))
    assert resp.status_code == 201
    return resp.json(), token


# ── Webhook WPPConnect ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_wppconnect_ignora_eventos_no_mensaje() -> None:
    """Eventos distintos a mensajes son ignorados sin error."""
    async with await _make_client() as client:
        resp = await client.post(
            "/webhooks/wppconnect",
            json={"event": "session_connected", "data": {}},
        )
    assert resp.status_code == 200
    assert resp.json()["skipped"] is True


@pytest.mark.asyncio
async def test_webhook_wppconnect_sin_numero_destino() -> None:
    """Si no hay número destino, el webhook responde OK pero skipped."""
    async with await _make_client() as client:
        resp = await client.post(
            "/webhooks/wppconnect",
            json={"event": "onmessage", "from": "5491111111111", "body": "Hola"},
        )
    assert resp.status_code == 200
    assert resp.json()["skipped"] is True


@pytest.mark.asyncio
async def test_webhook_wppconnect_numero_no_registrado() -> None:
    """Mensajes hacia un número no registrado son ignorados."""
    async with await _make_client() as client:
        resp = await client.post(
            "/webhooks/wppconnect",
            json={
                "event": "onmessage",
                "to": "99999999999@c.us",
                "from": "5491122223333@c.us",
                "body": "Quiero una pizza",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["skipped"] is True


@pytest.mark.asyncio
async def test_webhook_wppconnect_crea_sesion_y_mensaje() -> None:
    """Mensaje a número registrado crea sesión y guarda el mensaje."""
    with patch(
        "app.services.whatsapp._iniciar_sesion_wpp",
        new_callable=AsyncMock,
    ):
        async with await _make_client() as client:
            comercio, token = await _setup_comercio(client, "wh_msg")

            # Agregar número al comercio
            phone = f"+549{uuid.uuid4().int % 10**10:010d}"
            r_wa = await client.post(
                f"/comercios/{comercio['id']}/whatsapp",
                json={"phone_number": phone, "label": "Principal"},
                headers=_auth(token),
            )
            assert r_wa.status_code == 201

            # Simular número como conectado para poder buscar por él
            numero_id = r_wa.json()["id"]
            await client.patch(
                f"/comercios/{comercio['id']}/whatsapp/{numero_id}",
                json={"is_active": True},
                headers=_auth(token),
            )

            # Enviar webhook
            phone_clean = phone.lstrip("+")
            resp = await client.post(
                "/webhooks/wppconnect",
                json={
                    "event": "onmessage",
                    "to": f"{phone_clean}@c.us",
                    "from": "549111222333@c.us",
                    "body": "Quiero una muzza grande",
                },
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "session_id" in data


# ── Webhook MercadoPago ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_mp_ignora_tipos_desconocidos() -> None:
    """Tipos de notificación distintos a payment son ignorados."""
    async with await _make_client() as client:
        resp = await client.post(
            "/webhooks/mercadopago",
            json={"type": "merchant_order", "data": {"id": "12345"}},
        )
    assert resp.status_code == 200
    assert resp.json()["skipped"] is True


@pytest.mark.asyncio
async def test_webhook_mp_pago_aprobado_actualiza_pedido() -> None:
    """Webhook de pago aprobado actualiza payment_status del pedido."""
    order_id = str(uuid.uuid4())

    with patch(
        "app.api.webhooks.verificar_pago",
        new_callable=AsyncMock,
        return_value={
            "status": "approved",
            "external_reference": order_id,
            "transaction_amount": 1500,
        },
    ), patch(
        "app.api.webhooks.notificar_pago_confirmado",
        new_callable=AsyncMock,
    ):
        async with await _make_client() as client:
            resp = await client.post(
                "/webhooks/mercadopago",
                json={"type": "payment", "data": {"id": "mp_pay_001"}},
            )

    # El pedido no existe en DB, el webhook responde OK igualmente (skipped)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_webhook_mp_pago_no_aprobado_ignorado() -> None:
    """Webhook con pago no aprobado (pending, rejected) es ignorado."""
    with patch(
        "app.api.webhooks.verificar_pago",
        new_callable=AsyncMock,
        return_value={
            "status": "pending",
            "external_reference": str(uuid.uuid4()),
            "transaction_amount": 500,
        },
    ):
        async with await _make_client() as client:
            resp = await client.post(
                "/webhooks/mercadopago",
                json={"type": "payment", "data": {"id": "mp_pay_002"}},
            )

    assert resp.status_code == 200
    assert resp.json()["skipped"] is True
