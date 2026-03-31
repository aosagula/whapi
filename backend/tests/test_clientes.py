"""Tests de la Fase 7: listado de clientes, historial de pedidos y gestión de créditos."""
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


async def _setup(client: AsyncClient) -> tuple[str, str]:
    """Registra un dueño con comercio. Devuelve (token, comercio_id)."""
    resp = await client.post(
        "/auth/registro",
        json={
            "name": "Dueño Test",
            "email": _email("duenio"),
            "password": "password123",
            "account_type": "owner",
        },
    )
    assert resp.status_code == 201
    token = resp.json()["token"]["access_token"]

    resp = await client.post(
        "/comercios",
        json={"name": "Pizzería Fase7", "address": "Av. Test 789"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    cid = resp.json()["id"]
    return token, cid


async def _crear_cliente(client: AsyncClient, token: str, cid: str, phone: str, name: str) -> dict:
    """Helper: crea un cliente y devuelve su JSON."""
    resp = await client.post(
        f"/comercios/{cid}/clientes",
        json={"phone": phone, "name": name},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    return resp.json()


# ── Listado ───────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_listar_clientes_vacio():
    """El listado retorna total 0 cuando no hay clientes."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)
        resp = await client.get(f"/comercios/{cid}/clientes", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []


@pytest.mark.anyio
async def test_listar_clientes_paginado():
    """El listado pagina correctamente."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)
        for i in range(5):
            await _crear_cliente(client, token, cid, f"115555000{i}", f"Cliente {i}")

        resp = await client.get(
            f"/comercios/{cid}/clientes?page=1&page_size=3", headers=_auth(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3
        assert data["page"] == 1

        resp2 = await client.get(
            f"/comercios/{cid}/clientes?page=2&page_size=3", headers=_auth(token)
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert len(data2["items"]) == 2


@pytest.mark.anyio
async def test_listar_clientes_busqueda_por_nombre():
    """El parámetro q filtra por nombre (case-insensitive)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)
        await _crear_cliente(client, token, cid, "1150000001", "María López")
        await _crear_cliente(client, token, cid, "1150000002", "Juan Pérez")

        resp = await client.get(
            f"/comercios/{cid}/clientes?q=maría", headers=_auth(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "María López"


@pytest.mark.anyio
async def test_listar_clientes_busqueda_por_telefono():
    """El parámetro q filtra también por teléfono."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)
        await _crear_cliente(client, token, cid, "1199887766", "Pedro")
        await _crear_cliente(client, token, cid, "1100001111", "Ana")

        resp = await client.get(
            f"/comercios/{cid}/clientes?q=1199887766", headers=_auth(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["phone"] == "1199887766"


# ── Historial de pedidos del cliente ─────────────────────────────────────────

@pytest.mark.anyio
async def test_historial_pedidos_cliente_vacio():
    """Un cliente nuevo no tiene pedidos."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)
        cliente = await _crear_cliente(client, token, cid, "1155559999", "Sin Pedidos")

        resp = await client.get(
            f"/comercios/{cid}/clientes/{cliente['id']}/pedidos",
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.anyio
async def test_historial_pedidos_cliente_inexistente():
    """El endpoint retorna 404 si el cliente no existe."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/comercios/{cid}/clientes/{fake_id}/pedidos",
            headers=_auth(token),
        )
        assert resp.status_code == 404


# ── Créditos ──────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_ajustar_credito_positivo():
    """El dueño puede acreditar saldo a un cliente."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)
        cliente = await _crear_cliente(client, token, cid, "1155551111", "Carlos")

        resp = await client.post(
            f"/comercios/{cid}/clientes/{cliente['id']}/creditos",
            json={"amount": 500.0, "reason": "Ajuste manual por error"},
            headers=_auth(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["amount"] == 500.0
        assert data["reason"] == "Ajuste manual por error"

        # Verificar que el saldo se actualizó
        resp2 = await client.get(
            f"/comercios/{cid}/clientes/{cliente['id']}",
            headers=_auth(token),
        )
        assert resp2.json()["credit_balance"] == 500.0


@pytest.mark.anyio
async def test_ajustar_credito_negativo():
    """El dueño puede descontar saldo si hay suficiente balance."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)
        cliente = await _crear_cliente(client, token, cid, "1155552222", "Diana")

        # Primero acreditar
        await client.post(
            f"/comercios/{cid}/clientes/{cliente['id']}/creditos",
            json={"amount": 300.0},
            headers=_auth(token),
        )
        # Luego descontar
        resp = await client.post(
            f"/comercios/{cid}/clientes/{cliente['id']}/creditos",
            json={"amount": -100.0, "reason": "Uso de crédito"},
            headers=_auth(token),
        )
        assert resp.status_code == 201

        resp2 = await client.get(
            f"/comercios/{cid}/clientes/{cliente['id']}",
            headers=_auth(token),
        )
        assert resp2.json()["credit_balance"] == 200.0


@pytest.mark.anyio
async def test_ajustar_credito_saldo_insuficiente():
    """No se puede dejar saldo negativo."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)
        cliente = await _crear_cliente(client, token, cid, "1155553333", "Eduardo")

        resp = await client.post(
            f"/comercios/{cid}/clientes/{cliente['id']}/creditos",
            json={"amount": -50.0},
            headers=_auth(token),
        )
        assert resp.status_code == 422


@pytest.mark.anyio
async def test_ajustar_credito_requiere_gestion():
    """Un cajero no puede ajustar créditos."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)
        cliente = await _crear_cliente(client, token, cid, "1155554444", "Florencia")

        # Registrar empleado cajero
        resp_cajero = await client.post(
            "/auth/registro",
            json={
                "name": "Cajero",
                "email": _email("cajero"),
                "password": "password123",
                "account_type": "employee",
            },
        )
        cajero_id = resp_cajero.json()["id"]
        token_cajero = resp_cajero.json()["token"]["access_token"]

        # Asociar como cajero
        await client.post(
            f"/comercios/{cid}/empleados",
            json={"user_id": cajero_id, "role": "cashier"},
            headers=_auth(token),
        )

        resp = await client.post(
            f"/comercios/{cid}/clientes/{cliente['id']}/creditos",
            json={"amount": 100.0},
            headers=_auth(token_cajero),
        )
        assert resp.status_code == 403


@pytest.mark.anyio
async def test_listar_creditos_del_cliente():
    """El historial de créditos devuelve todos los movimientos ordenados."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)
        cliente = await _crear_cliente(client, token, cid, "1155555555", "Gustavo")
        cid_str = cid
        cli_id = cliente["id"]

        await client.post(
            f"/comercios/{cid_str}/clientes/{cli_id}/creditos",
            json={"amount": 200.0, "reason": "Cancelación pedido #1"},
            headers=_auth(token),
        )
        await client.post(
            f"/comercios/{cid_str}/clientes/{cli_id}/creditos",
            json={"amount": -50.0, "reason": "Uso en pedido #2"},
            headers=_auth(token),
        )

        resp = await client.get(
            f"/comercios/{cid_str}/clientes/{cli_id}/creditos",
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Ordenado por fecha desc → el último primero
        assert data[0]["reason"] == "Uso en pedido #2"
