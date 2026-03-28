"""Tests de autenticación: registro, login, perfil y mis-comercios."""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "http://test"


def _email(tag: str) -> str:
    """Genera un email único por ejecución para evitar colisiones en la DB real."""
    return f"{tag}_{uuid.uuid4().hex[:8]}@test.com"


async def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE)


# ── Registro ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_registro_dueno_ok() -> None:
    """Un dueño se registra correctamente y recibe token."""
    async with await _make_client() as client:
        resp = await client.post(
            "/auth/registro",
            json={
                "name": "Ana García",
                "email": _email("ana"),
                "password": "secreto123",
                "account_type": "owner",
            },
        )
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert data["token"]["access_token"]
    assert data["account_type"] == "owner"


@pytest.mark.asyncio
async def test_registro_empleado_ok() -> None:
    """Un empleado se registra correctamente."""
    async with await _make_client() as client:
        resp = await client.post(
            "/auth/registro",
            json={
                "name": "Carlos López",
                "email": _email("carlos"),
                "password": "secreto123",
                "account_type": "employee",
            },
        )
    assert resp.status_code == 201
    assert resp.json()["account_type"] == "employee"


@pytest.mark.asyncio
async def test_registro_email_duplicado() -> None:
    """No se puede registrar dos veces con el mismo email."""
    email = _email("dup")
    payload = {
        "name": "Dup User",
        "email": email,
        "password": "secreto123",
        "account_type": "owner",
    }
    async with await _make_client() as client:
        await client.post("/auth/registro", json=payload)
        resp = await client.post("/auth/registro", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_registro_password_corta() -> None:
    """Contraseña menor a 8 caracteres es rechazada."""
    async with await _make_client() as client:
        resp = await client.post(
            "/auth/registro",
            json={
                "name": "Test",
                "email": _email("short"),
                "password": "123",
                "account_type": "employee",
            },
        )
    assert resp.status_code == 422


# ── Login ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_ok() -> None:
    """Login correcto retorna un token JWT."""
    email = _email("loginok")
    async with await _make_client() as client:
        await client.post(
            "/auth/registro",
            json={
                "name": "Login User",
                "email": email,
                "password": "mipassword",
                "account_type": "owner",
            },
        )
        resp = await client.post(
            "/auth/login",
            json={"email": email, "password": "mipassword"},
        )
    assert resp.status_code == 200
    assert resp.json()["access_token"]
    assert resp.json()["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_password_incorrecta() -> None:
    """Login con contraseña incorrecta retorna 401."""
    email = _email("wrongpass")
    async with await _make_client() as client:
        await client.post(
            "/auth/registro",
            json={
                "name": "Wrong Pass",
                "email": email,
                "password": "correctpass",
                "account_type": "employee",
            },
        )
        resp = await client.post(
            "/auth/login",
            json={"email": email, "password": "mal"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_email_inexistente() -> None:
    """Login con email no registrado retorna 401."""
    async with await _make_client() as client:
        resp = await client.post(
            "/auth/login",
            json={"email": _email("noexiste"), "password": "cualquier"},
        )
    assert resp.status_code == 401


# ── /auth/me ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_me_ok() -> None:
    """/auth/me retorna el perfil del usuario autenticado."""
    email = _email("meuser")
    async with await _make_client() as client:
        reg = await client.post(
            "/auth/registro",
            json={
                "name": "Me User",
                "email": email,
                "password": "mipassword",
                "account_type": "owner",
            },
        )
        token = reg.json()["token"]["access_token"]
        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.json()["email"] == email


@pytest.mark.asyncio
async def test_me_sin_token() -> None:
    """/auth/me sin token retorna 401 o 403."""
    async with await _make_client() as client:
        resp = await client.get("/auth/me")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_token_invalido() -> None:
    """/auth/me con token inválido retorna 401."""
    async with await _make_client() as client:
        resp = await client.get("/auth/me", headers={"Authorization": "Bearer tokenmalo"})
    assert resp.status_code == 401


# ── /comercios/mis-comercios ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mis_comercios_sin_comercios() -> None:
    """Un usuario recién registrado no tiene comercios asociados."""
    async with await _make_client() as client:
        reg = await client.post(
            "/auth/registro",
            json={
                "name": "Sin Comercio",
                "email": _email("sincomercio"),
                "password": "mipassword",
                "account_type": "owner",
            },
        )
        token = reg.json()["token"]["access_token"]
        resp = await client.get(
            "/comercios/mis-comercios",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    assert resp.json()["comercios"] == []


@pytest.mark.asyncio
async def test_mis_comercios_sin_auth() -> None:
    """/comercios/mis-comercios sin token retorna 401 o 403."""
    async with await _make_client() as client:
        resp = await client.get("/comercios/mis-comercios")
    assert resp.status_code in (401, 403)
