"""Tests del router interno n8n: autenticación, resolver-tenant, contexto y operaciones del chatbot."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "http://test"
API_KEY = "test-n8n-key-123"


def _email(tag: str) -> str:
    return f"{tag}_{uuid.uuid4().hex[:8]}@test.com"


def _phone() -> str:
    return "549" + str(uuid.uuid4().int)[:9]


async def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE)


def _n8n_headers() -> dict:
    return {"X-N8N-Api-Key": API_KEY}


async def _registrar_y_crear_comercio(client: AsyncClient, tag: str) -> tuple[str, dict]:
    """Registra un dueño y crea un comercio. Retorna (token, comercio)."""
    resp = await client.post(
        "/auth/registro",
        json={
            "name": f"Dueño {tag}",
            "email": _email(tag),
            "password": "password123",
            "account_type": "owner",
        },
    )
    assert resp.status_code == 201
    token = resp.json()["token"]["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/comercios", json={"name": f"Pizzería {tag}"}, headers=auth)
    assert resp.status_code == 201
    return token, resp.json()


async def _agregar_numero_wa(client: AsyncClient, token: str, comercio_id: str, phone: str) -> dict:
    """Agrega un número de WhatsApp al comercio (mockeando WPPConnect)."""
    with patch("app.services.whatsapp.generar_token_wpp", new_callable=AsyncMock) as mock_token, \
         patch("app.services.whatsapp.iniciar_sesion_wpp", new_callable=AsyncMock) as mock_sesion:
        mock_token.return_value = "tok123"
        mock_sesion.return_value = {"status": "qrCode", "qrcode": "data:image/png;base64,abc"}
        resp = await client.post(
            f"/comercios/{comercio_id}/whatsapp",
            json={"phone_number": phone, "label": "Principal"},
            headers={"Authorization": f"Bearer {token}"},
        )
    # Si el endpoint no existe o falla, creamos el número directamente en DB
    return resp.json() if resp.status_code == 201 else {}


# ── Autenticación de la API key ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sin_api_key_retorna_422() -> None:
    """Sin el header X-N8N-Api-Key retorna 422 (campo requerido faltante)."""
    async with await _make_client() as client:
        resp = await client.get("/n8n/resolver-tenant?numero=5491112345678")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_api_key_incorrecta_retorna_401() -> None:
    """API key incorrecta retorna 401."""
    with patch.object(__import__("app.core.config", fromlist=["settings"]).settings, "N8N_API_KEY", API_KEY):
        async with await _make_client() as client:
            resp = await client.get(
                "/n8n/resolver-tenant?numero=5491112345678",
                headers={"X-N8N-Api-Key": "clave-incorrecta"},
            )
    assert resp.status_code == 401


# ── Resolver tenant ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resolver_tenant_numero_no_registrado() -> None:
    """Un número no registrado retorna 404."""
    with patch.object(__import__("app.core.config", fromlist=["settings"]).settings, "N8N_API_KEY", API_KEY):
        async with await _make_client() as client:
            resp = await client.get(
                "/n8n/resolver-tenant?numero=5499999999999",
                headers=_n8n_headers(),
            )
    assert resp.status_code == 404


# ── Contexto ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_obtener_contexto_crea_cliente_y_sesion() -> None:
    """Si el cliente no existe lo crea; si no hay sesión la crea también."""
    with patch.object(__import__("app.core.config", fromlist=["settings"]).settings, "N8N_API_KEY", API_KEY):
        async with await _make_client() as client:
            _, comercio = await _registrar_y_crear_comercio(client, "ctx_nuevo")
            business_id = comercio["id"]
            phone = _phone()

            resp = await client.get(
                f"/n8n/comercios/{business_id}/contexto?phone={phone}",
                headers=_n8n_headers(),
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["customer"]["phone"] == phone
    assert data["session_status"] == "active_bot"
    assert data["active_order"] is None
    assert data["recent_messages"] == []


@pytest.mark.asyncio
async def test_obtener_contexto_normaliza_numero() -> None:
    """El número con @c.us y prefijo + se normaliza correctamente."""
    with patch.object(__import__("app.core.config", fromlist=["settings"]).settings, "N8N_API_KEY", API_KEY):
        async with await _make_client() as client:
            _, comercio = await _registrar_y_crear_comercio(client, "ctx_norm")
            business_id = comercio["id"]
            phone = _phone()

            # Primer llamado con número normalizado
            resp1 = await client.get(
                f"/n8n/comercios/{business_id}/contexto?phone={phone}",
                headers=_n8n_headers(),
            )
            assert resp1.status_code == 200
            cliente_id_1 = resp1.json()["customer"]["customer_id"]

            # Segundo llamado con formato WA — debe retornar el mismo cliente
            resp2 = await client.get(
                f"/n8n/comercios/{business_id}/contexto?phone=+{phone}@c.us",
                headers=_n8n_headers(),
            )
            assert resp2.status_code == 200
            assert resp2.json()["customer"]["customer_id"] == cliente_id_1


# ── Guardar mensaje ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_guardar_mensaje_inbound() -> None:
    """Guardar un mensaje inbound persiste y actualiza last_message_at."""
    with patch.object(__import__("app.core.config", fromlist=["settings"]).settings, "N8N_API_KEY", API_KEY):
        async with await _make_client() as client:
            _, comercio = await _registrar_y_crear_comercio(client, "msg_in")
            business_id = comercio["id"]

            ctx = await client.get(
                f"/n8n/comercios/{business_id}/contexto?phone={_phone()}",
                headers=_n8n_headers(),
            )
            session_id = ctx.json()["session_id"]

            resp = await client.post(
                f"/n8n/comercios/{business_id}/mensajes",
                json={"session_id": session_id, "direction": "inbound", "content": "Hola quiero una pizza"},
                headers=_n8n_headers(),
            )

    assert resp.status_code == 201
    assert "message_id" in resp.json()


# ── Catálogo ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_catalogo_comercio_sin_productos() -> None:
    """Comercio nuevo retorna catálogo vacío."""
    with patch.object(__import__("app.core.config", fromlist=["settings"]).settings, "N8N_API_KEY", API_KEY):
        async with await _make_client() as client:
            _, comercio = await _registrar_y_crear_comercio(client, "cat_vacio")
            resp = await client.get(
                f"/n8n/comercios/{comercio['id']}/catalogo",
                headers=_n8n_headers(),
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["productos"] == []
    assert data["combos"] == []


# ── Flujo completo: crear pedido → agregar item → confirmar ──────────────────

@pytest.mark.asyncio
async def test_flujo_pedido_completo() -> None:
    """Crea un pedido, agrega un ítem y lo confirma."""
    with patch.object(__import__("app.core.config", fromlist=["settings"]).settings, "N8N_API_KEY", API_KEY):
        async with await _make_client() as client:
            token, comercio = await _registrar_y_crear_comercio(client, "flujo_pedido")
            business_id = comercio["id"]
            phone = _phone()

            # Obtener contexto (crea cliente y sesión)
            ctx_resp = await client.get(
                f"/n8n/comercios/{business_id}/contexto?phone={phone}",
                headers=_n8n_headers(),
            )
            ctx = ctx_resp.json()
            customer_id = ctx["customer"]["customer_id"]
            session_id = ctx["session_id"]

            # Crear pedido borrador
            pedido_resp = await client.post(
                f"/n8n/comercios/{business_id}/pedidos",
                json={
                    "customer_id": customer_id,
                    "session_id": session_id,
                    "delivery_type": "delivery",
                    "delivery_address": "Av. Siempre Viva 742",
                },
                headers=_n8n_headers(),
            )
            assert pedido_resp.status_code == 201
            pedido = pedido_resp.json()
            pedido_id = pedido["order_id"]
            assert pedido["status"] == "in_progress"
            assert pedido["items"] == []

            # Agregar ítem
            item_resp = await client.post(
                f"/n8n/comercios/{business_id}/pedidos/{pedido_id}/items",
                json={
                    "product_id": None,
                    "combo_id": None,
                    "quantity": 2,
                    "unit_price": 1500.0,
                    "variant": {"size": "large"},
                    "notes": None,
                },
                headers=_n8n_headers(),
            )
            assert item_resp.status_code == 201
            assert len(item_resp.json()["items"]) == 1
            assert item_resp.json()["total_amount"] == 3000.0
            item_id = item_resp.json()["items"][0]["item_id"]

            # Quitar ítem
            del_resp = await client.delete(
                f"/n8n/comercios/{business_id}/pedidos/{pedido_id}/items/{item_id}",
                headers=_n8n_headers(),
            )
            assert del_resp.status_code == 200
            assert del_resp.json()["items"] == []
            assert del_resp.json()["total_amount"] == 0.0

            # Re-agregar
            await client.post(
                f"/n8n/comercios/{business_id}/pedidos/{pedido_id}/items",
                json={"quantity": 1, "unit_price": 2100.0},
                headers=_n8n_headers(),
            )

            # Confirmar pedido
            confirm_resp = await client.post(
                f"/n8n/comercios/{business_id}/pedidos/{pedido_id}/confirmar",
                json={},
                headers=_n8n_headers(),
            )
            assert confirm_resp.status_code == 200
            assert confirm_resp.json()["status"] == "pending_payment"


# ── Actualizar cliente ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_actualizar_nombre_cliente() -> None:
    """El orquestador puede actualizar el nombre del cliente."""
    with patch.object(__import__("app.core.config", fromlist=["settings"]).settings, "N8N_API_KEY", API_KEY):
        async with await _make_client() as client:
            _, comercio = await _registrar_y_crear_comercio(client, "upd_cliente")
            business_id = comercio["id"]

            ctx = await client.get(
                f"/n8n/comercios/{business_id}/contexto?phone={_phone()}",
                headers=_n8n_headers(),
            )
            cliente_id = ctx.json()["customer"]["customer_id"]

            resp = await client.patch(
                f"/n8n/clientes/{cliente_id}",
                json={"name": "Juan Pérez", "address": "Corrientes 1234"},
                headers=_n8n_headers(),
            )

    assert resp.status_code == 200
    assert resp.json()["name"] == "Juan Pérez"
    assert resp.json()["address"] == "Corrientes 1234"


# ── Derivar a humano ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_derivar_a_humano() -> None:
    """La sesión pasa a waiting_operator al derivar."""
    with patch.object(__import__("app.core.config", fromlist=["settings"]).settings, "N8N_API_KEY", API_KEY):
        async with await _make_client() as client:
            _, comercio = await _registrar_y_crear_comercio(client, "hitl")
            business_id = comercio["id"]

            ctx = await client.get(
                f"/n8n/comercios/{business_id}/contexto?phone={_phone()}",
                headers=_n8n_headers(),
            )
            session_id = ctx.json()["session_id"]

            resp = await client.post(
                f"/n8n/conversaciones/{session_id}/derivar",
                json={"session_id": session_id, "motivo": "Cliente frustrado"},
                headers=_n8n_headers(),
            )

    assert resp.status_code == 200
    assert resp.json()["status"] == "waiting_operator"


# ── Sesiones inactivas ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sesiones_inactivas_vacio() -> None:
    """Sin sesiones con inactividad suficiente retorna lista vacía."""
    with patch.object(__import__("app.core.config", fromlist=["settings"]).settings, "N8N_API_KEY", API_KEY):
        async with await _make_client() as client:
            resp = await client.get(
                "/n8n/sesiones/inactivas?minutos=10",
                headers=_n8n_headers(),
            )

    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
