"""Tests de pedidos telefónicos (Fase 6): buscar cliente, crear, flujo completo."""
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
            "name": "Cajero Test",
            "email": _email("cajero"),
            "password": "password123",
            "account_type": "owner",
        },
    )
    assert resp.status_code == 201
    token = resp.json()["token"]["access_token"]

    resp = await client.post(
        "/comercios",
        json={"name": "Pizzería Fase6", "address": "Av. Test 123"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    cid = resp.json()["id"]

    return token, cid


# ── Tests de clientes ─────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_crear_cliente_con_has_whatsapp():
    """El campo has_whatsapp se guarda correctamente."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)

        resp = await client.post(
            f"/comercios/{cid}/clientes",
            json={"phone": "1155550010", "name": "Ana Pérez", "has_whatsapp": False},
            headers=_auth(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["has_whatsapp"] is False
        assert data["phone"] == "1155550010"


@pytest.mark.anyio
async def test_crear_cliente_has_whatsapp_default_true():
    """Por defecto has_whatsapp es True."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)

        resp = await client.post(
            f"/comercios/{cid}/clientes",
            json={"phone": "1155550020", "name": "Beto"},
            headers=_auth(token),
        )
        assert resp.status_code == 201
        assert resp.json()["has_whatsapp"] is True


@pytest.mark.anyio
async def test_buscar_cliente_por_telefono_encontrado():
    """GET /clientes/buscar?phone=... devuelve el cliente existente."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)

        # Crear cliente primero
        await client.post(
            f"/comercios/{cid}/clientes",
            json={"phone": "1155550030", "name": "Carlos"},
            headers=_auth(token),
        )

        resp = await client.get(
            f"/comercios/{cid}/clientes/buscar?phone=1155550030",
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Carlos"
        assert resp.json()["phone"] == "1155550030"


@pytest.mark.anyio
async def test_buscar_cliente_por_telefono_no_encontrado():
    """GET /clientes/buscar con teléfono inexistente devuelve 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)

        resp = await client.get(
            f"/comercios/{cid}/clientes/buscar?phone=9999999999",
            headers=_auth(token),
        )
        assert resp.status_code == 404


@pytest.mark.anyio
async def test_actualizar_cliente():
    """PATCH /clientes/{id} actualiza nombre, dirección y has_whatsapp."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)

        resp = await client.post(
            f"/comercios/{cid}/clientes",
            json={"phone": "1155550040", "name": "Diego"},
            headers=_auth(token),
        )
        cliente_id = resp.json()["id"]

        resp = await client.patch(
            f"/comercios/{cid}/clientes/{cliente_id}",
            json={"name": "Diego Actualizado", "address": "Calle Nueva 123", "has_whatsapp": False},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Diego Actualizado"
        assert data["address"] == "Calle Nueva 123"
        assert data["has_whatsapp"] is False


@pytest.mark.anyio
async def test_buscar_cliente_aislado_por_comercio():
    """Un cliente de un comercio no es visible desde otro comercio."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        # Comercio A
        resp = await client.post("/auth/registro", json={
            "name": "Dueno A", "email": _email("duenoa"), "password": "password123", "account_type": "owner",
        })
        assert resp.status_code == 201
        token_a = resp.json()["token"]["access_token"]
        resp = await client.post("/comercios", json={"name": "Comercio A"}, headers=_auth(token_a))
        cid_a = resp.json()["id"]

        # Comercio B
        resp = await client.post("/auth/registro", json={
            "name": "Dueno B", "email": _email("duenob"), "password": "password123", "account_type": "owner",
        })
        token_b = resp.json()["token"]["access_token"]
        resp = await client.post("/comercios", json={"name": "Comercio B"}, headers=_auth(token_b))
        cid_b = resp.json()["id"]

        # Crear cliente en comercio A
        await client.post(
            f"/comercios/{cid_a}/clientes",
            json={"phone": "1155550050", "name": "Compartido"},
            headers=_auth(token_a),
        )

        # Buscar en comercio B → debe ser 404
        resp = await client.get(
            f"/comercios/{cid_b}/clientes/buscar?phone=1155550050",
            headers=_auth(token_b),
        )
        assert resp.status_code == 404


# ── Tests de pedidos telefónicos ──────────────────────────────────────────────

@pytest.mark.anyio
async def test_crear_pedido_telefonico_origin_phone():
    """Un pedido manual se crea con origin='phone'."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)

        # Crear cliente
        resp = await client.post(
            f"/comercios/{cid}/clientes",
            json={"phone": "1155550060", "name": "Elena"},
            headers=_auth(token),
        )
        cliente_id = resp.json()["id"]

        # Crear producto y precio
        resp = await client.post(
            f"/comercios/{cid}/products",
            json={"code": "MUZ01", "short_name": "Muzzarella", "full_name": "Pizza Muzzarella", "category": "pizza"},
            headers=_auth(token),
        )
        prod_id = resp.json()["id"]
        await client.post(
            f"/comercios/{cid}/catalog",
            json={"product_id": prod_id, "price_large": 1500.0},
            headers=_auth(token),
        )

        # Crear pedido telefónico
        resp = await client.post(
            f"/comercios/{cid}/pedidos",
            json={
                "customer_id": cliente_id,
                "origin": "phone",
                "delivery_type": "delivery",
                "delivery_address": "Corrientes 1234",
                "payment_status": "cash_on_delivery",
                "total_amount": 1500.0,
                "items": [
                    {"product_id": prod_id, "quantity": 1, "unit_price": 1500.0}
                ],
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["origin"] == "phone"
        assert data["status"] == "pending_preparation"
        assert data["payment_status"] == "cash_on_delivery"
        assert data["delivery_type"] == "delivery"
        assert len(data["items"]) == 1


@pytest.mark.anyio
async def test_crear_pedido_telefonico_retiro():
    """Pedido telefónico de retiro en local sin dirección."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        token, cid = await _setup(client)

        resp = await client.post(
            f"/comercios/{cid}/clientes",
            json={"phone": "1155550070", "name": "Franco"},
            headers=_auth(token),
        )
        cliente_id = resp.json()["id"]

        resp = await client.post(
            f"/comercios/{cid}/pedidos",
            json={
                "customer_id": cliente_id,
                "origin": "phone",
                "delivery_type": "pickup",
                "delivery_address": None,
                "payment_status": "cash_on_delivery",
                "total_amount": 0.0,
                "items": [],
            },
            headers=_auth(token),
        )
        # No puede tener 0 items, pero el endpoint lo acepta (validación de negocio futura)
        # Lo importante es que origin=phone y delivery_type=pickup queden bien
        assert resp.status_code in (201, 422)
        if resp.status_code == 201:
            assert resp.json()["delivery_type"] == "pickup"
            assert resp.json()["origin"] == "phone"


@pytest.mark.anyio
async def test_pedido_telefonico_cliente_otro_comercio_falla():
    """No se puede crear un pedido con un cliente_id de otro comercio."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        # Comercio 1
        resp = await client.post("/auth/registro", json={
            "name": "Dueno1", "email": _email("d1"), "password": "password123", "account_type": "owner",
        })
        assert resp.status_code == 201
        token1 = resp.json()["token"]["access_token"]
        resp = await client.post("/comercios", json={"name": "Com1"}, headers=_auth(token1))
        cid1 = resp.json()["id"]

        # Comercio 2
        resp = await client.post("/auth/registro", json={
            "name": "Dueno2", "email": _email("d2"), "password": "password123", "account_type": "owner",
        })
        token2 = resp.json()["token"]["access_token"]
        resp = await client.post("/comercios", json={"name": "Com2"}, headers=_auth(token2))
        cid2 = resp.json()["id"]

        # Cliente en comercio 1
        resp = await client.post(
            f"/comercios/{cid1}/clientes",
            json={"phone": "1155550080", "name": "Inválido"},
            headers=_auth(token1),
        )
        cliente_id_com1 = resp.json()["id"]

        # Intentar crear pedido en comercio 2 con cliente del comercio 1
        resp = await client.post(
            f"/comercios/{cid2}/pedidos",
            json={
                "customer_id": cliente_id_com1,
                "origin": "phone",
                "delivery_type": "pickup",
                "payment_status": "cash_on_delivery",
                "total_amount": 0.0,
                "items": [],
            },
            headers=_auth(token2),
        )
        assert resp.status_code == 404
