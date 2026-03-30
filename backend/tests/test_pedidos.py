"""Tests del módulo de pedidos: tablero, estados, cancelaciones e incidencias."""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "http://test"


def _email(tag: str) -> str:
    return f"{tag}_{uuid.uuid4().hex[:8]}@test.com"


async def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _setup_completo(client: AsyncClient) -> tuple[str, str, str]:
    """Registra un dueño, crea un comercio y un cliente. Devuelve (token, comercio_id, cliente_id)."""
    resp = await client.post(
        "/auth/registro",
        json={
            "name": "Dueño Test",
            "email": _email("dueno"),
            "password": "password123",
            "account_type": "owner",
        },
    )
    assert resp.status_code == 201
    token = resp.json()["token"]["access_token"]

    resp = await client.post(
        "/comercios",
        json={"name": "Pizzería Test", "address": "Av. Siempre Viva 742"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    cid = resp.json()["id"]

    # Crear cliente para el comercio
    resp = await client.post(
        f"/comercios/{cid}/clientes",
        json={"phone": "1155550001", "name": "Juan Test"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    cliente_id = resp.json()["id"]

    return token, cid, cliente_id


async def _crear_pedido(
    client: AsyncClient, token: str, cid: str, cliente_id: str
) -> dict:
    """Crea un pedido manual de prueba y retorna el JSON de respuesta."""
    resp = await client.post(
        f"/comercios/{cid}/pedidos",
        json={
            "customer_id": cliente_id,
            "origin": "operator",
            "delivery_type": "delivery",
            "delivery_address": "Calle Falsa 123",
            "payment_status": "no_charge",
            "total_amount": 2500.0,
            "credit_applied": 0,
            "items": [],
        },
        headers=_auth(token),
    )
    assert resp.status_code == 201
    return resp.json()


# ── Listado ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_listar_pedidos_vacio() -> None:
    """El tablero de un comercio nuevo devuelve lista vacía."""
    async with await _make_client() as client:
        token, cid, _ = await _setup_completo(client)
        resp = await client.get(f"/comercios/{cid}/pedidos", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []


@pytest.mark.asyncio
async def test_listar_pedidos_con_datos() -> None:
    """El tablero muestra los pedidos creados."""
    async with await _make_client() as client:
        token, cid, cliente_id = await _setup_completo(client)
        await _crear_pedido(client, token, cid, cliente_id)
        await _crear_pedido(client, token, cid, cliente_id)

        resp = await client.get(f"/comercios/{cid}/pedidos", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2


# ── Detalle ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_obtener_detalle_pedido() -> None:
    """El detalle de un pedido incluye historial y cliente."""
    async with await _make_client() as client:
        token, cid, cliente_id = await _setup_completo(client)
        pedido = await _crear_pedido(client, token, cid, cliente_id)
        pedido_id = pedido["id"]

        resp = await client.get(
            f"/comercios/{cid}/pedidos/{pedido_id}", headers=_auth(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == pedido_id
        assert data["order_number"] >= 1
        assert data["customer"]["phone"] == "1155550001"
        assert len(data["status_history"]) >= 1


# ── Número de pedido ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_order_number_incremental() -> None:
    """Los pedidos reciben números consecutivos dentro del mismo comercio."""
    async with await _make_client() as client:
        token, cid, cliente_id = await _setup_completo(client)
        p1 = await _crear_pedido(client, token, cid, cliente_id)
        p2 = await _crear_pedido(client, token, cid, cliente_id)
        assert p2["order_number"] == p1["order_number"] + 1


# ── Cambio de estado ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_avanzar_estado_ok() -> None:
    """El dueño puede avanzar el pedido de pending_preparation a in_preparation."""
    async with await _make_client() as client:
        token, cid, cliente_id = await _setup_completo(client)
        pedido = await _crear_pedido(client, token, cid, cliente_id)
        pedido_id = pedido["id"]
        assert pedido["status"] == "pending_preparation"

        resp = await client.patch(
            f"/comercios/{cid}/pedidos/{pedido_id}/estado",
            json={"status": "in_preparation", "note": "Empezando a preparar"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "in_preparation"
        # El historial registra el cambio
        assert any(
            h["new_status"] == "in_preparation" for h in data["status_history"]
        )


@pytest.mark.asyncio
async def test_transicion_invalida() -> None:
    """No se puede hacer una transición no permitida."""
    async with await _make_client() as client:
        token, cid, cliente_id = await _setup_completo(client)
        pedido = await _crear_pedido(client, token, cid, cliente_id)
        pedido_id = pedido["id"]

        # Desde pending_preparation no se puede ir a delivered directamente
        resp = await client.patch(
            f"/comercios/{cid}/pedidos/{pedido_id}/estado",
            json={"status": "delivered"},
            headers=_auth(token),
        )
        assert resp.status_code == 400


# ── Pago ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_marcar_pagado() -> None:
    """El cajero puede marcar un pedido como pagado."""
    async with await _make_client() as client:
        token, cid, cliente_id = await _setup_completo(client)
        pedido = await _crear_pedido(client, token, cid, cliente_id)
        pedido_id = pedido["id"]

        resp = await client.patch(
            f"/comercios/{cid}/pedidos/{pedido_id}/pago",
            json={"payment_status": "paid"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json()["payment_status"] == "paid"


# ── Notas internas ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_actualizar_notas() -> None:
    """Se pueden guardar notas internas en un pedido."""
    async with await _make_client() as client:
        token, cid, cliente_id = await _setup_completo(client)
        pedido = await _crear_pedido(client, token, cid, cliente_id)
        pedido_id = pedido["id"]

        resp = await client.patch(
            f"/comercios/{cid}/pedidos/{pedido_id}/notas",
            json={"internal_notes": "Sin sal en las empanadas"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json()["internal_notes"] == "Sin sal en las empanadas"


# ── Cancelación ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancelar_sin_cargo() -> None:
    """Cancelar un pedido en pending_preparation sin pago previo → no_charge."""
    async with await _make_client() as client:
        token, cid, cliente_id = await _setup_completo(client)
        pedido = await _crear_pedido(client, token, cid, cliente_id)
        pedido_id = pedido["id"]

        resp = await client.post(
            f"/comercios/{cid}/pedidos/{pedido_id}/cancelar",
            json={"note": "Cliente canceló"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cancelled"
        assert data["payment_status"] == "no_charge"


@pytest.mark.asyncio
async def test_cancelar_con_credito() -> None:
    """Cancelar un pedido ya pagado en pending_preparation → crédito a favor."""
    async with await _make_client() as client:
        token, cid, cliente_id = await _setup_completo(client)
        pedido = await _crear_pedido(client, token, cid, cliente_id)
        pedido_id = pedido["id"]

        # Marcar como pagado primero
        await client.patch(
            f"/comercios/{cid}/pedidos/{pedido_id}/pago",
            json={"payment_status": "paid"},
            headers=_auth(token),
        )

        resp = await client.post(
            f"/comercios/{cid}/pedidos/{pedido_id}/cancelar",
            json={},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cancelled"
        assert data["payment_status"] == "credit"


@pytest.mark.asyncio
async def test_no_cancelar_entregado() -> None:
    """No se puede cancelar un pedido ya entregado."""
    async with await _make_client() as client:
        token, cid, cliente_id = await _setup_completo(client)
        pedido = await _crear_pedido(client, token, cid, cliente_id)
        pedido_id = pedido["id"]

        # Avanzar hasta delivered
        for estado in ["in_preparation", "to_dispatch", "in_delivery", "delivered"]:
            await client.patch(
                f"/comercios/{cid}/pedidos/{pedido_id}/estado",
                json={"status": estado},
                headers=_auth(token),
            )

        resp = await client.post(
            f"/comercios/{cid}/pedidos/{pedido_id}/cancelar",
            json={},
            headers=_auth(token),
        )
        assert resp.status_code == 400


# ── Incidencias ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reportar_incidencia() -> None:
    """Se puede reportar una incidencia en un pedido."""
    async with await _make_client() as client:
        token, cid, cliente_id = await _setup_completo(client)
        pedido = await _crear_pedido(client, token, cid, cliente_id)
        pedido_id = pedido["id"]

        resp = await client.post(
            f"/comercios/{cid}/pedidos/{pedido_id}/incidencia",
            json={"type": "wrong_order", "description": "Enviaron la pizza equivocada"},
            headers=_auth(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "with_incident"
        assert len(data["incidents"]) == 1
        assert data["incidents"][0]["type"] == "wrong_order"


# ── Tenant isolation ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pedido_aislamiento_por_comercio() -> None:
    """Un usuario no puede ver pedidos de otro comercio."""
    async with await _make_client() as client:
        token1, cid1, cliente_id1 = await _setup_completo(client)
        token2, cid2, _ = await _setup_completo(client)
        pedido = await _crear_pedido(client, token1, cid1, cliente_id1)
        pedido_id = pedido["id"]

        # Token2 no puede ver el pedido del comercio 1
        resp = await client.get(
            f"/comercios/{cid2}/pedidos/{pedido_id}", headers=_auth(token2)
        )
        assert resp.status_code == 404
