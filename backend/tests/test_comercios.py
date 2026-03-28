"""Tests de comercios y empleados."""
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


async def _registrar(client: AsyncClient, tag: str, tipo: str = "owner") -> dict:
    """Registra un usuario y retorna sus datos con token."""
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


# ── Crear comercio ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_crear_comercio_ok() -> None:
    """Un dueño puede crear un comercio y queda asociado como owner."""
    async with await _make_client() as client:
        dueno = await _registrar(client, "crea1")
        token = dueno["token"]["access_token"]

        resp = await client.post(
            "/comercios",
            json={"name": "Pizzería Test", "address": "Av. Siempre Viva 742"},
            headers=_auth(token),
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Pizzería Test"
    assert data["role"] == "owner"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_crear_comercio_sin_auth() -> None:
    """Crear comercio sin token retorna 401/403."""
    async with await _make_client() as client:
        resp = await client.post("/comercios", json={"name": "X"})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_mis_comercios_incluye_nuevo() -> None:
    """Después de crear un comercio aparece en mis-comercios."""
    async with await _make_client() as client:
        dueno = await _registrar(client, "mis1")
        token = dueno["token"]["access_token"]
        await client.post("/comercios", json={"name": "Mi Pizzería"}, headers=_auth(token))

        resp = await client.get("/comercios/mis-comercios", headers=_auth(token))

    assert resp.status_code == 200
    nombres = [c["name"] for c in resp.json()["comercios"]]
    assert "Mi Pizzería" in nombres


# ── Detalle y edición ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_detalle_comercio_ok() -> None:
    """El owner puede ver el detalle de su comercio."""
    async with await _make_client() as client:
        dueno = await _registrar(client, "det1")
        token = dueno["token"]["access_token"]
        comer = (await client.post("/comercios", json={"name": "Det Pizzería"}, headers=_auth(token))).json()

        resp = await client.get(f"/comercios/{comer['id']}", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["name"] == "Det Pizzería"


@pytest.mark.asyncio
async def test_detalle_comercio_no_miembro() -> None:
    """Un usuario ajeno no puede ver el comercio."""
    async with await _make_client() as client:
        dueno = await _registrar(client, "det2a")
        ajeno = await _registrar(client, "det2b")
        token_dueno = dueno["token"]["access_token"]
        token_ajeno = ajeno["token"]["access_token"]
        comer = (await client.post("/comercios", json={"name": "Privado"}, headers=_auth(token_dueno))).json()

        resp = await client.get(f"/comercios/{comer['id']}", headers=_auth(token_ajeno))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_editar_comercio_ok() -> None:
    """El owner puede editar el nombre del comercio."""
    async with await _make_client() as client:
        dueno = await _registrar(client, "edit1")
        token = dueno["token"]["access_token"]
        comer = (await client.post("/comercios", json={"name": "Antes"}, headers=_auth(token))).json()

        resp = await client.patch(
            f"/comercios/{comer['id']}",
            json={"name": "Después"},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Después"


# ── Empleados ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_listar_empleados_solo_owner_inicial() -> None:
    """Al crear un comercio, el único miembro es el owner."""
    async with await _make_client() as client:
        dueno = await _registrar(client, "listemp1")
        token = dueno["token"]["access_token"]
        comer = (await client.post("/comercios", json={"name": "Emp Test"}, headers=_auth(token))).json()

        resp = await client.get(f"/comercios/{comer['id']}/empleados", headers=_auth(token))
    assert resp.status_code == 200
    empleados = resp.json()
    assert len(empleados) == 1
    assert empleados[0]["role"] == "owner"


@pytest.mark.asyncio
async def test_asociar_empleado_ok() -> None:
    """El owner puede asociar un usuario existente como cajero."""
    async with await _make_client() as client:
        dueno = await _registrar(client, "asoc1")
        empleado = await _registrar(client, "asoc1emp", "employee")
        token_dueno = dueno["token"]["access_token"]
        comer = (await client.post("/comercios", json={"name": "Asoc Test"}, headers=_auth(token_dueno))).json()

        resp = await client.post(
            f"/comercios/{comer['id']}/empleados",
            json={"email": empleado["email"], "role": "cashier"},
            headers=_auth(token_dueno),
        )
    assert resp.status_code == 201
    assert resp.json()["role"] == "cashier"
    assert resp.json()["email"] == empleado["email"]


@pytest.mark.asyncio
async def test_asociar_empleado_email_inexistente() -> None:
    """Asociar un email que no existe retorna 404."""
    async with await _make_client() as client:
        dueno = await _registrar(client, "asoc2")
        token = dueno["token"]["access_token"]
        comer = (await client.post("/comercios", json={"name": "X"}, headers=_auth(token))).json()

        resp = await client.post(
            f"/comercios/{comer['id']}/empleados",
            json={"email": "noexiste@x.com", "role": "cashier"},
            headers=_auth(token),
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_asociar_empleado_duplicado() -> None:
    """Asociar el mismo usuario dos veces retorna 409."""
    async with await _make_client() as client:
        dueno = await _registrar(client, "asoc3")
        emp = await _registrar(client, "asoc3emp", "employee")
        token = dueno["token"]["access_token"]
        comer = (await client.post("/comercios", json={"name": "X"}, headers=_auth(token))).json()
        payload = {"email": emp["email"], "role": "cashier"}

        await client.post(f"/comercios/{comer['id']}/empleados", json=payload, headers=_auth(token))
        resp = await client.post(f"/comercios/{comer['id']}/empleados", json=payload, headers=_auth(token))
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_cambiar_rol_empleado_ok() -> None:
    """El owner puede cambiar el rol de un empleado."""
    async with await _make_client() as client:
        dueno = await _registrar(client, "rol1")
        emp = await _registrar(client, "rol1emp", "employee")
        token = dueno["token"]["access_token"]
        comer = (await client.post("/comercios", json={"name": "X"}, headers=_auth(token))).json()
        emp_resp = (await client.post(
            f"/comercios/{comer['id']}/empleados",
            json={"email": emp["email"], "role": "cashier"},
            headers=_auth(token),
        )).json()

        resp = await client.patch(
            f"/comercios/{comer['id']}/empleados/{emp_resp['user_id']}",
            json={"role": "cook"},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert resp.json()["role"] == "cook"


@pytest.mark.asyncio
async def test_dar_de_baja_empleado_ok() -> None:
    """El owner puede dar de baja a un empleado."""
    async with await _make_client() as client:
        dueno = await _registrar(client, "baja1")
        emp = await _registrar(client, "baja1emp", "employee")
        token = dueno["token"]["access_token"]
        comer = (await client.post("/comercios", json={"name": "X"}, headers=_auth(token))).json()
        emp_resp = (await client.post(
            f"/comercios/{comer['id']}/empleados",
            json={"email": emp["email"], "role": "cashier"},
            headers=_auth(token),
        )).json()

        resp = await client.delete(
            f"/comercios/{comer['id']}/empleados/{emp_resp['user_id']}",
            headers=_auth(token),
        )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_dar_de_baja_owner_falla() -> None:
    """No se puede dar de baja al owner del comercio."""
    async with await _make_client() as client:
        dueno = await _registrar(client, "baja2")
        token = dueno["token"]["access_token"]
        comer = (await client.post("/comercios", json={"name": "X"}, headers=_auth(token))).json()
        empleados = (await client.get(f"/comercios/{comer['id']}/empleados", headers=_auth(token))).json()
        owner_id = empleados[0]["user_id"]

        resp = await client.delete(
            f"/comercios/{comer['id']}/empleados/{owner_id}",
            headers=_auth(token),
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_cajero_no_puede_gestionar_empleados() -> None:
    """Un cajero no puede asociar ni dar de baja empleados."""
    async with await _make_client() as client:
        dueno = await _registrar(client, "cajero1")
        cajero_user = await _registrar(client, "cajero1emp", "employee")
        token_dueno = dueno["token"]["access_token"]
        token_cajero = cajero_user["token"]["access_token"]
        comer = (await client.post("/comercios", json={"name": "X"}, headers=_auth(token_dueno))).json()
        await client.post(
            f"/comercios/{comer['id']}/empleados",
            json={"email": cajero_user["email"], "role": "cashier"},
            headers=_auth(token_dueno),
        )

        # El cajero intenta agregar otro empleado
        otro = await _registrar(client, "cajero1otro", "employee")
        resp = await client.post(
            f"/comercios/{comer['id']}/empleados",
            json={"email": otro["email"], "role": "cook"},
            headers=_auth(token_cajero),
        )
    assert resp.status_code == 403
