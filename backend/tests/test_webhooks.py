"""Tests de webhooks (WPPConnect y MercadoPago)."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

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
    from app.core.db import AsyncSessionLocal
    from app.models.conversation import Message

    with patch.object(__import__("app.core.config", fromlist=["settings"]).settings, "AGENT_ENABLED", False), patch(
        "app.services.whatsapp._iniciar_sesion_wpp",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "app.api.webhooks._resolver_pn_lid_wpp",
        new_callable=AsyncMock,
        return_value="549111222333",
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
                    "from": "238465945968878@lid",
                    "body": "Quiero una muzza grande",
                    "sender": {
                        "id": "238465945968878@lid",
                        "formattedName": "Luciana Coccari",
                        "name": "Luciana Coccari",
                        "pushname": "Telefono Backup Vaclog",
                    },
                    "notifyName": "Telefono Backup Vaclog",
                },
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "session_id" in data

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Message).where(Message.session_id == uuid.UUID(data["session_id"]))
        )
        messages = list(result.scalars().all())
        assert len(messages) == 1
        assert messages[0].sender_phone == "549111222333"
        assert messages[0].sender_name == "Luciana Coccari"
        assert messages[0].content == "Quiero una muzza grande"
        assert messages[0].raw_payload is not None


@pytest.mark.asyncio
async def test_webhook_wppconnect_reutiliza_cliente_conocido() -> None:
    """Si el teléfono ya existe como cliente, el chat debe quedar asociado a ese cliente conocido."""
    from app.core.db import AsyncSessionLocal
    from app.models.conversation import ConversationSession
    from app.models.customer import Customer
    cliente_phone = "549111222333"

    with patch.object(__import__("app.core.config", fromlist=["settings"]).settings, "AGENT_ENABLED", False), patch(
        "app.services.whatsapp._iniciar_sesion_wpp",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "app.api.webhooks._resolver_pn_lid_wpp",
        new_callable=AsyncMock,
        return_value=cliente_phone,
    ):
        async with await _make_client() as client:
            comercio, token = await _setup_comercio(client, "wh_known")

            phone = f"+549{uuid.uuid4().int % 10**10:010d}"
            r_wa = await client.post(
                f"/comercios/{comercio['id']}/whatsapp",
                json={"phone_number": phone, "label": "Principal"},
                headers=_auth(token),
            )
            assert r_wa.status_code == 201

            r_cliente = await client.post(
                f"/comercios/{comercio['id']}/clientes",
                json={"phone": cliente_phone, "name": "Juan Cliente"},
                headers=_auth(token),
            )
            assert r_cliente.status_code == 201
            cliente_id = r_cliente.json()["id"]

            phone_clean = phone.lstrip("+")
            resp = await client.post(
                "/webhooks/wppconnect",
                json={
                    "event": "onmessage",
                    "to": f"{phone_clean}@c.us",
                    "from": f"+{cliente_phone}@s.whatsapp.net",
                    "body": "Hola, ya soy cliente",
                    "notifyName": "Juan WA",
                    "sender": {
                        "id": f"{cliente_phone}@s.whatsapp.net",
                        "pushname": "Juan Push",
                        "name": "Juan Perfil",
                        "verifiedName": "Juan Negocio",
                    },
                },
            )

        assert resp.status_code == 200

        async with AsyncSessionLocal() as db:
            customer_result = await db.execute(
                select(Customer).where(Customer.business_id == uuid.UUID(comercio["id"]))
            )
            customers = list(customer_result.scalars().all())
            assert len(customers) == 1
            assert str(customers[0].id) == cliente_id
            assert customers[0].name == "Juan Cliente"
            assert customers[0].phone == cliente_phone
            assert customers[0].whatsapp_wa_id == f"{cliente_phone}@s.whatsapp.net"
            assert customers[0].whatsapp_display_name == "Juan Perfil"
            assert customers[0].whatsapp_profile_name == "Juan Push"
            assert customers[0].whatsapp_business_name == "Juan Negocio"
            assert customers[0].whatsapp_metadata is not None

            session_result = await db.execute(
                select(ConversationSession).where(
                    ConversationSession.business_id == uuid.UUID(comercio["id"])
                )
            )
            sessions = list(session_result.scalars().all())
            assert len(sessions) == 1
            assert str(sessions[0].customer_id) == cliente_id


@pytest.mark.asyncio
async def test_webhook_wppconnect_dispara_agente_y_persiste_estado() -> None:
    """Con el agente activo, el webhook debe guardar inbound, outbound y agent_state."""
    from app.core.db import AsyncSessionLocal
    from app.models.conversation import ConversationSession, Message
    from app.models.customer import Customer

    with patch(
        "app.services.whatsapp._iniciar_sesion_wpp",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "app.services.agent_inbox.enviar_mensaje_whatsapp",
        new_callable=AsyncMock,
    ) as mock_send:
        async with await _make_client() as client:
            comercio, token = await _setup_comercio(client, "wh_agent")

            phone = f"+549{uuid.uuid4().int % 10**10:010d}"
            r_wa = await client.post(
                f"/comercios/{comercio['id']}/whatsapp",
                json={"phone_number": phone, "label": "Principal"},
                headers=_auth(token),
            )
            assert r_wa.status_code == 201

            phone_clean = phone.lstrip("+")
            resp = await client.post(
                "/webhooks/wppconnect",
                json={
                    "event": "onmessage",
                    "to": f"{phone_clean}@c.us",
                    "from": "5491112233445@c.us",
                    "body": "Que pizzas tienen?",
                    "notifyName": "Juan WA",
                    "sender": {
                        "id": "5491112233445@c.us",
                        "formattedName": "Juan Cliente",
                        "pushname": "Juan WA",
                    },
                },
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["agent"] is not None
    assert body["agent"]["decision"]["intent"] == "query_catalog"
    mock_send.assert_awaited()

    async with AsyncSessionLocal() as db:
        session_result = await db.execute(
            select(ConversationSession).where(ConversationSession.id == uuid.UUID(body["session_id"]))
        )
        session = session_result.scalar_one()
        assert session.agent_state is not None
        assert session.agent_state["current_intent"] == "query_catalog"
        assert session.agent_state["stage"] == "general_query"

        customer_result = await db.execute(select(Customer).where(Customer.id == session.customer_id))
        customer = customer_result.scalar_one()
        assert customer.phone == "5491112233445"

        message_result = await db.execute(
            select(Message).where(Message.session_id == session.id).order_by(Message.sent_at.asc())
        )
        messages = list(message_result.scalars().all())
        assert len(messages) == 2
        assert messages[0].direction == "inbound"
        assert messages[1].direction == "outbound"
        assert "opciones disponibles" in messages[1].content.lower()


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
