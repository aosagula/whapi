"""Tests del endpoint de generación de link de pago."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "http://test"


def _email(tag: str) -> str:
    return f"{tag}_{uuid.uuid4().hex[:8]}@test.com"


def _phone() -> str:
    return "+549" + str(uuid.uuid4().int)[:9]


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


async def _setup(client: AsyncClient, tag: str) -> tuple[dict, str]:
    user = await _registrar(client, tag)
    token = user["token"]["access_token"]
    resp = await client.post("/comercios", json={"name": f"Pizzería {tag}"}, headers=_auth(token))
    assert resp.status_code == 201
    return resp.json(), token


async def _crear_cliente(client: AsyncClient, comercio_id: str, token: str) -> dict:
    resp = await client.post(
        f"/comercios/{comercio_id}/clientes",
        json={"phone": _phone(), "name": "Cliente Test"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    return resp.json()


async def _crear_pedido_pendiente(client: AsyncClient, comercio_id: str, token: str, cliente_id: str) -> dict:
    """Crea un pedido con payment_status=pending_payment."""
    # Primero necesitamos un producto
    r_prod = await client.post(
        f"/comercios/{comercio_id}/products",
        json={"code": f"P{uuid.uuid4().hex[:4]}", "short_name": "Muzza", "full_name": "Pizza Muzza", "category": "pizza"},
        headers=_auth(token),
    )
    assert r_prod.status_code == 201
    product_id = r_prod.json()["id"]

    resp = await client.post(
        f"/comercios/{comercio_id}/pedidos",
        json={
            "customer_id": cliente_id,
            "origin": "whatsapp",
            "delivery_type": "delivery",
            "payment_status": "pending_payment",
            "total_amount": 1500,
            "items": [{"product_id": product_id, "quantity": 1, "unit_price": 1500}],
        },
        headers=_auth(token),
    )
    assert resp.status_code == 201
    return resp.json()


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generar_link_pago_ok() -> None:
    """Owner puede generar link de pago para un pedido con pago pendiente."""
    mock_pref = {
        "preference_id": "PREF-123",
        "init_point": "https://mp.com/checkout/PREF-123",
        "sandbox_init_point": "https://sandbox.mp.com/checkout/PREF-123",
    }
    with patch(
        "app.api.pagos.crear_preferencia",
        new_callable=AsyncMock,
        return_value=mock_pref,
    ), patch(
        "app.api.pagos.notificar_link_pago",
        new_callable=AsyncMock,
    ):
        async with await _make_client() as client:
            comercio, token = await _setup(client, "pago_ok")
            cliente = await _crear_cliente(client, comercio["id"], token)
            pedido = await _crear_pedido_pendiente(client, comercio["id"], token, cliente["id"])

            resp = await client.post(
                f"/comercios/{comercio['id']}/pedidos/{pedido['id']}/pago-link",
                headers=_auth(token),
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["preference_id"] == "PREF-123"
    assert "init_point" in data


@pytest.mark.asyncio
async def test_generar_link_pago_pedido_ya_pagado_falla() -> None:
    """No se puede generar link si el pedido ya está pagado."""
    async with await _make_client() as client:
        comercio, token = await _setup(client, "pago_paid")
        cliente = await _crear_cliente(client, comercio["id"], token)

        # Crear pedido con pago ya confirmado
        r_prod = await client.post(
            f"/comercios/{comercio['id']}/products",
            json={"code": f"P{uuid.uuid4().hex[:4]}", "short_name": "Muzza", "full_name": "Pizza Muzza", "category": "pizza"},
            headers=_auth(token),
        )
        product_id = r_prod.json()["id"]

        pedido = await client.post(
            f"/comercios/{comercio['id']}/pedidos",
            json={
                "customer_id": cliente["id"],
                "origin": "whatsapp",
                "delivery_type": "delivery",
                "payment_status": "paid",
                "total_amount": 1000,
                "items": [{"product_id": product_id, "quantity": 1, "unit_price": 1000}],
            },
            headers=_auth(token),
        )
        assert pedido.status_code == 201

        resp = await client.post(
            f"/comercios/{comercio['id']}/pedidos/{pedido.json()['id']}/pago-link",
            headers=_auth(token),
        )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_generar_link_pago_sin_permiso() -> None:
    """Un cajero no puede generar links de pago (requiere owner o admin)."""
    async with await _make_client() as client:
        comercio, token_owner = await _setup(client, "pago_perm")
        cliente = await _crear_cliente(client, comercio["id"], token_owner)
        pedido = await _crear_pedido_pendiente(client, comercio["id"], token_owner, cliente["id"])

        # Registrar cajero y asociarlo
        cajero = await _registrar(client, "pago_cajero")
        await client.post(
            f"/comercios/{comercio['id']}/empleados",
            json={"email": cajero["email"], "role": "cashier"},
            headers=_auth(token_owner),
        )
        token_cajero = cajero["token"]["access_token"]

        resp = await client.post(
            f"/comercios/{comercio['id']}/pedidos/{pedido['id']}/pago-link",
            headers=_auth(token_cajero),
        )

    assert resp.status_code == 403
