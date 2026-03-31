"""Tests de conversaciones HITL (Fase 8): listado, detalle, transiciones de estado."""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "http://test"


def _email(tag: str) -> str:
    return f"{tag}_{uuid.uuid4().hex[:8]}@test.com"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Setup helpers ─────────────────────────────────────────────────────────────

async def _setup(client: AsyncClient) -> tuple[str, str, str]:
    """Registra un dueño, crea un comercio y un cliente. Devuelve (token, comercio_id, cliente_id)."""
    resp = await client.post(
        "/auth/registro",
        json={
            "name": "Dueño HITL",
            "email": _email("hitl"),
            "password": "password123",
            "account_type": "owner",
        },
    )
    assert resp.status_code == 201
    token = resp.json()["token"]["access_token"]

    resp = await client.post(
        "/comercios",
        json={"name": "Pizzería HITL", "address": "Av. Test 100"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    cid = resp.json()["id"]

    resp = await client.post(
        f"/comercios/{cid}/clientes",
        json={"phone": "1155551234", "name": "Cliente HITL"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    cliente_id = resp.json()["id"]

    return token, cid, cliente_id


async def _crear_sesion_waiting(
    client: AsyncClient, token: str, cid: str, cliente_id: str
) -> str:
    """Inserta una sesión en estado waiting_operator directamente vía DB helper del test."""
    from app.core.db import AsyncSessionLocal
    from app.models.conversation import ConversationSession

    async with AsyncSessionLocal() as db:
        session = ConversationSession(
            business_id=uuid.UUID(cid),
            customer_id=uuid.UUID(cliente_id),
            status="waiting_operator",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return str(session.id)


# ── Tests de listado ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_listar_conversaciones_vacio():
    """El listado retorna lista vacía cuando no hay sesiones activas."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid, _ = await _setup(client)
        resp = await client.get(f"/comercios/{cid}/conversaciones", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.anyio
async def test_listar_conversaciones_muestra_waiting():
    """Las sesiones en waiting_operator aparecen en el listado."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid, cliente_id = await _setup(client)
        session_id = await _crear_sesion_waiting(client, token, cid, cliente_id)

        resp = await client.get(f"/comercios/{cid}/conversaciones", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == session_id
        assert data[0]["status"] == "waiting_operator"
        assert data[0]["customer"]["phone"] == "1155551234"


@pytest.mark.anyio
async def test_listar_conversaciones_no_muestra_cerradas():
    """Las sesiones closed o active_bot no aparecen en el listado."""
    from app.core.db import AsyncSessionLocal
    from app.models.conversation import ConversationSession

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid, cliente_id = await _setup(client)

        # Crear sesión cerrada
        async with AsyncSessionLocal() as db:
            session = ConversationSession(
                business_id=uuid.UUID(cid),
                customer_id=uuid.UUID(cliente_id),
                status="closed",
            )
            db.add(session)
            await db.commit()

        resp = await client.get(f"/comercios/{cid}/conversaciones", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.anyio
async def test_listar_conversaciones_cocinero_no_tiene_acceso():
    """El cocinero recibe 403 al intentar ver conversaciones."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid, _ = await _setup(client)

        # Crear empleado cocinero
        resp_cook = await client.post(
            "/auth/registro",
            json={"name": "Cocinero", "email": _email("cook"), "password": "password123", "account_type": "employee"},
        )
        cook_id = resp_cook.json()["id"]
        token_cook = resp_cook.json()["token"]["access_token"]
        await client.post(
            f"/comercios/{cid}/empleados",
            json={"user_id": cook_id, "role": "cook"},
            headers=_auth(token),
        )

        resp = await client.get(f"/comercios/{cid}/conversaciones", headers=_auth(token_cook))
        assert resp.status_code == 403


# ── Tests de detalle ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_obtener_conversacion_detalle():
    """El detalle de una sesión incluye mensajes y datos del cliente."""
    from app.core.db import AsyncSessionLocal
    from app.models.conversation import ConversationSession, Message

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid, cliente_id = await _setup(client)

        async with AsyncSessionLocal() as db:
            session = ConversationSession(
                business_id=uuid.UUID(cid),
                customer_id=uuid.UUID(cliente_id),
                status="waiting_operator",
            )
            db.add(session)
            await db.flush()
            msg = Message(session_id=session.id, direction="inbound", content="Hola quiero una pizza")
            db.add(msg)
            await db.commit()
            session_id = str(session.id)

        resp = await client.get(f"/comercios/{cid}/conversaciones/{session_id}", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == session_id
        assert data["customer"]["phone"] == "1155551234"
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "Hola quiero una pizza"
        assert data["messages"][0]["direction"] == "inbound"


@pytest.mark.anyio
async def test_obtener_conversacion_inexistente():
    """Retorna 404 para una sesión que no existe en el comercio."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid, _ = await _setup(client)
        resp = await client.get(f"/comercios/{cid}/conversaciones/{uuid.uuid4()}", headers=_auth(token))
        assert resp.status_code == 404


# ── Tests de transiciones ─────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_atender_conversacion():
    """El operador toma una sesión en waiting_operator → assigned_human."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid, cliente_id = await _setup(client)
        session_id = await _crear_sesion_waiting(client, token, cid, cliente_id)

        resp = await client.post(
            f"/comercios/{cid}/conversaciones/{session_id}/atender",
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "assigned_human"
        assert data["assigned_operator_id"] is not None


@pytest.mark.anyio
async def test_atender_sesion_ya_asignada_falla():
    """No se puede tomar una sesión que ya está assigned_human."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid, cliente_id = await _setup(client)
        session_id = await _crear_sesion_waiting(client, token, cid, cliente_id)

        # Primera vez: OK
        await client.post(f"/comercios/{cid}/conversaciones/{session_id}/atender", headers=_auth(token))

        # Segunda vez: conflicto
        resp = await client.post(
            f"/comercios/{cid}/conversaciones/{session_id}/atender",
            headers=_auth(token),
        )
        assert resp.status_code == 409


@pytest.mark.anyio
async def test_enviar_mensaje_operador():
    """El operador puede enviar un mensaje cuando la sesión está en assigned_human."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid, cliente_id = await _setup(client)
        session_id = await _crear_sesion_waiting(client, token, cid, cliente_id)

        # Tomar la sesión primero
        await client.post(f"/comercios/{cid}/conversaciones/{session_id}/atender", headers=_auth(token))

        resp = await client.post(
            f"/comercios/{cid}/conversaciones/{session_id}/mensaje",
            json={"content": "Hola, te atiende un humano. ¿En qué te ayudo?"},
            headers=_auth(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["direction"] == "outbound"
        assert data["content"] == "Hola, te atiende un humano. ¿En qué te ayudo?"


@pytest.mark.anyio
async def test_enviar_mensaje_sin_asignar_falla():
    """No se puede enviar mensajes en una sesión que no está assigned_human."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid, cliente_id = await _setup(client)
        session_id = await _crear_sesion_waiting(client, token, cid, cliente_id)

        resp = await client.post(
            f"/comercios/{cid}/conversaciones/{session_id}/mensaje",
            json={"content": "mensaje"},
            headers=_auth(token),
        )
        assert resp.status_code == 409


@pytest.mark.anyio
async def test_enviar_mensaje_vacio_falla():
    """El mensaje vacío es rechazado con 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid, cliente_id = await _setup(client)
        session_id = await _crear_sesion_waiting(client, token, cid, cliente_id)
        await client.post(f"/comercios/{cid}/conversaciones/{session_id}/atender", headers=_auth(token))

        resp = await client.post(
            f"/comercios/{cid}/conversaciones/{session_id}/mensaje",
            json={"content": "   "},
            headers=_auth(token),
        )
        assert resp.status_code == 422


@pytest.mark.anyio
async def test_devolver_al_bot():
    """El operador puede devolver el control al LLM: assigned_human → active_bot."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid, cliente_id = await _setup(client)
        session_id = await _crear_sesion_waiting(client, token, cid, cliente_id)
        await client.post(f"/comercios/{cid}/conversaciones/{session_id}/atender", headers=_auth(token))

        resp = await client.post(
            f"/comercios/{cid}/conversaciones/{session_id}/devolver-al-bot",
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "active_bot"
        assert data["assigned_operator_id"] is None


@pytest.mark.anyio
async def test_devolver_al_bot_sin_asignar_falla():
    """No se puede devolver al bot si la sesión no está en assigned_human."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid, cliente_id = await _setup(client)
        session_id = await _crear_sesion_waiting(client, token, cid, cliente_id)

        resp = await client.post(
            f"/comercios/{cid}/conversaciones/{session_id}/devolver-al-bot",
            headers=_auth(token),
        )
        assert resp.status_code == 409


@pytest.mark.anyio
async def test_cerrar_sin_pedido():
    """El operador puede cerrar una sesión derivada: assigned_human → closed."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid, cliente_id = await _setup(client)
        session_id = await _crear_sesion_waiting(client, token, cid, cliente_id)
        await client.post(f"/comercios/{cid}/conversaciones/{session_id}/atender", headers=_auth(token))

        resp = await client.post(
            f"/comercios/{cid}/conversaciones/{session_id}/cerrar",
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"

        # La sesión cerrada no aparece en el listado
        lista = await client.get(f"/comercios/{cid}/conversaciones", headers=_auth(token))
        assert lista.json() == []


@pytest.mark.anyio
async def test_cerrar_descarta_pedido_en_curso():
    """Al cerrar una sesión, el pedido en curso queda en estado discarded."""
    from app.core.db import AsyncSessionLocal
    from app.models.conversation import ConversationSession
    from app.models.order import Order

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid, cliente_id = await _setup(client)

        async with AsyncSessionLocal() as db:
            session = ConversationSession(
                business_id=uuid.UUID(cid),
                customer_id=uuid.UUID(cliente_id),
                status="waiting_operator",
            )
            db.add(session)
            await db.flush()

            # Pedido en curso ligado a la sesión
            order = Order(
                business_id=uuid.UUID(cid),
                customer_id=uuid.UUID(cliente_id),
                session_id=session.id,
                order_number=999,
                status="in_progress",
                payment_status="no_charge",
                origin="whatsapp",
                delivery_type="delivery",
                total_amount=0,
                credit_applied=0,
            )
            db.add(order)
            await db.commit()
            session_id = str(session.id)
            order_id = str(order.id)

        # Atender y cerrar
        await client.post(f"/comercios/{cid}/conversaciones/{session_id}/atender", headers=_auth(token))
        await client.post(f"/comercios/{cid}/conversaciones/{session_id}/cerrar", headers=_auth(token))

        # Verificar que el pedido quedó en discarded
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                __import__("sqlalchemy", fromlist=["select"]).select(Order).where(Order.id == uuid.UUID(order_id))
            )
            updated_order = result.scalar_one()
            assert updated_order.status == "discarded"
