"""Tests de gestión de números de WhatsApp."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "http://test"


def _email(tag: str) -> str:
    return f"{tag}_{uuid.uuid4().hex[:8]}@test.com"


def _phone() -> str:
    """Genera un número de teléfono único para tests."""
    return "+549" + str(uuid.uuid4().int)[:9]


async def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE)


async def _registrar(client: AsyncClient, tag: str, tipo: str = "owner") -> dict:
    resp = await client.post(
        "/auth/registro",
        json={
            "name": f"User {tag}",
            "email": _email(tag),
            "password": "password123",
            "account_type": tipo,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _crear_comercio(client: AsyncClient, token: str) -> dict:
    resp = await client.post(
        "/comercios",
        json={"name": "Pizzería WA Test"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    return resp.json()


# ── Listar (vacío inicial) ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_listar_numeros_vacio() -> None:
    """Un comercio nuevo no tiene números registrados."""
    async with await _make_client() as client:
        dueno = await _registrar(client, "wa_list")
        token = dueno["token"]["access_token"]
        comercio = await _crear_comercio(client, token)

        resp = await client.get(
            f"/comercios/{comercio['id']}/whatsapp",
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert resp.json() == []


# ── Agregar número ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agregar_numero_ok() -> None:
    """Owner puede agregar un número de WhatsApp."""
    # Mockeamos WPPConnect para no necesitar servidor real
    with patch(
        "app.services.whatsapp._iniciar_sesion_wpp",
        new_callable=AsyncMock,
    ):
        async with await _make_client() as client:
            dueno = await _registrar(client, "wa_add")
            token = dueno["token"]["access_token"]
            comercio = await _crear_comercio(client, token)

            phone = _phone()
            resp = await client.post(
                f"/comercios/{comercio['id']}/whatsapp",
                json={"phone_number": phone, "label": "Número principal"},
                headers=_auth(token),
            )
    assert resp.status_code == 201
    data = resp.json()
    assert data["phone_number"] == phone
    assert data["label"] == "Número principal"
    assert data["status"] == "scanning"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_agregar_numero_duplicado() -> None:
    """No se puede agregar el mismo número dos veces al mismo comercio."""
    with patch(
        "app.services.whatsapp._iniciar_sesion_wpp",
        new_callable=AsyncMock,
    ):
        async with await _make_client() as client:
            dueno = await _registrar(client, "wa_dup")
            token = dueno["token"]["access_token"]
            comercio = await _crear_comercio(client, token)

            payload = {"phone_number": _phone(), "label": "Principal"}

            r1 = await client.post(
                f"/comercios/{comercio['id']}/whatsapp",
                json=payload,
                headers=_auth(token),
            )
            assert r1.status_code == 201

            r2 = await client.post(
                f"/comercios/{comercio['id']}/whatsapp",
                json=payload,
                headers=_auth(token),
            )
    assert r2.status_code == 409


# ── Editar ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_editar_etiqueta() -> None:
    """Owner puede cambiar la etiqueta de un número."""
    with patch(
        "app.services.whatsapp._iniciar_sesion_wpp",
        new_callable=AsyncMock,
    ):
        async with await _make_client() as client:
            dueno = await _registrar(client, "wa_edit")
            token = dueno["token"]["access_token"]
            comercio = await _crear_comercio(client, token)

            r_add = await client.post(
                f"/comercios/{comercio['id']}/whatsapp",
                json={"phone_number": _phone(), "label": "Original"},
                headers=_auth(token),
            )
            assert r_add.status_code == 201
            numero_id = r_add.json()["id"]

            r_edit = await client.patch(
                f"/comercios/{comercio['id']}/whatsapp/{numero_id}",
                json={"label": "Zona Norte"},
                headers=_auth(token),
            )
    assert r_edit.status_code == 200
    assert r_edit.json()["label"] == "Zona Norte"


# ── Eliminar ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_eliminar_numero() -> None:
    """Owner puede eliminar un número (soft delete: is_active=False)."""
    with patch(
        "app.services.whatsapp._iniciar_sesion_wpp",
        new_callable=AsyncMock,
    ), patch(
        "app.services.whatsapp._cerrar_sesion_wpp",
        new_callable=AsyncMock,
    ):
        async with await _make_client() as client:
            dueno = await _registrar(client, "wa_del")
            token = dueno["token"]["access_token"]
            comercio = await _crear_comercio(client, token)

            r_add = await client.post(
                f"/comercios/{comercio['id']}/whatsapp",
                json={"phone_number": _phone(), "label": "Temporal"},
                headers=_auth(token),
            )
            assert r_add.status_code == 201
            numero_id = r_add.json()["id"]

            r_del = await client.delete(
                f"/comercios/{comercio['id']}/whatsapp/{numero_id}",
                headers=_auth(token),
            )
            assert r_del.status_code == 204

            # El número aún aparece en la lista pero inactivo
            r_list = await client.get(
                f"/comercios/{comercio['id']}/whatsapp",
                headers=_auth(token),
            )
    numeros = r_list.json()
    encontrado = next((n for n in numeros if n["id"] == numero_id), None)
    assert encontrado is not None
    assert encontrado["is_active"] is False


# ── Control de acceso ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empleado_sin_rol_gestion_no_puede_listar() -> None:
    """Un cajero no puede acceder a la gestión de WhatsApp."""
    async with await _make_client() as client:
        dueno = await _registrar(client, "wa_acl_owner")
        token_dueno = dueno["token"]["access_token"]
        comercio = await _crear_comercio(client, token_dueno)

        cajero = await _registrar(client, "wa_acl_cajero", tipo="employee")
        token_cajero = cajero["token"]["access_token"]

        # Asociar cajero al comercio
        await client.post(
            f"/comercios/{comercio['id']}/empleados",
            json={"email": cajero["email"], "role": "cashier"},
            headers=_auth(token_dueno),
        )

        resp = await client.get(
            f"/comercios/{comercio['id']}/whatsapp",
            headers=_auth(token_cajero),
        )
    assert resp.status_code == 403
