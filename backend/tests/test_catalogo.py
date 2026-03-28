"""Tests del catálogo: productos, precios y combos."""
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


async def _setup(client: AsyncClient) -> tuple[str, str]:
    """Registra un dueño, crea un comercio y devuelve (token, comercio_id)."""
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
    data = resp.json()
    token = data["token"]["access_token"]

    resp = await client.post(
        "/comercios",
        json={"name": "Pizzería Test", "address": "Av. Siempre Viva 742"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    comercio_id = resp.json()["id"]
    return token, comercio_id


# ── Productos ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_crear_producto_ok() -> None:
    """Un admin puede crear un producto en el inventario."""
    async with await _make_client() as client:
        token, cid = await _setup(client)
        resp = await client.post(
            f"/comercios/{cid}/products",
            json={
                "code": "PIZ-MOZ",
                "short_name": "Mozza",
                "full_name": "Pizza Mozzarella",
                "description": "Salsa de tomate, mozzarella",
                "category": "pizza",
            },
            headers=_auth(token),
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "PIZ-MOZ"
    assert data["category"] == "pizza"
    assert data["is_available"] is True


@pytest.mark.asyncio
async def test_codigo_duplicado_409() -> None:
    """No se puede crear un producto con el mismo código en el mismo comercio."""
    async with await _make_client() as client:
        token, cid = await _setup(client)
        payload = {
            "code": "PIZ-FUG",
            "short_name": "Fugazzeta",
            "full_name": "Pizza Fugazzeta",
            "category": "pizza",
        }
        r1 = await client.post(f"/comercios/{cid}/products", json=payload, headers=_auth(token))
        assert r1.status_code == 201
        r2 = await client.post(f"/comercios/{cid}/products", json=payload, headers=_auth(token))
        assert r2.status_code == 409


@pytest.mark.asyncio
async def test_editar_producto_no_cambia_codigo() -> None:
    """El código no se modifica al editar un producto."""
    async with await _make_client() as client:
        token, cid = await _setup(client)
        # Crear
        create_resp = await client.post(
            f"/comercios/{cid}/products",
            json={"code": "EMP-CAR", "short_name": "Carne", "full_name": "Empanada de Carne", "category": "empanada"},
            headers=_auth(token),
        )
        assert create_resp.status_code == 201
        pid = create_resp.json()["id"]

        # Editar solo el nombre
        edit_resp = await client.patch(
            f"/comercios/{cid}/products/{pid}",
            json={"short_name": "Carne suave"},
            headers=_auth(token),
        )
        assert edit_resp.status_code == 200
        data = edit_resp.json()
        assert data["code"] == "EMP-CAR"  # inmutable
        assert data["short_name"] == "Carne suave"


@pytest.mark.asyncio
async def test_listar_productos_con_filtros() -> None:
    """Listar productos filtrando por categoría."""
    async with await _make_client() as client:
        token, cid = await _setup(client)
        headers = _auth(token)
        await client.post(
            f"/comercios/{cid}/products",
            json={"code": "PIZ-NAP", "short_name": "Napo", "full_name": "Pizza Napolitana", "category": "pizza"},
            headers=headers,
        )
        await client.post(
            f"/comercios/{cid}/products",
            json={"code": "BEB-COCA", "short_name": "Coca 1.5L", "full_name": "Coca-Cola 1.5L", "category": "drink"},
            headers=headers,
        )

        resp = await client.get(f"/comercios/{cid}/products?category=pizza", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert all(p["category"] == "pizza" for p in data["items"])


@pytest.mark.asyncio
async def test_desactivar_producto() -> None:
    """Se puede desactivar un producto (soft delete disponible)."""
    async with await _make_client() as client:
        token, cid = await _setup(client)
        resp = await client.post(
            f"/comercios/{cid}/products",
            json={"code": "BEB-FAN", "short_name": "Fanta", "full_name": "Fanta 600ml", "category": "drink"},
            headers=_auth(token),
        )
        assert resp.status_code == 201
        pid = resp.json()["id"]

        # Desactivar via PATCH
        patch_resp = await client.patch(
            f"/comercios/{cid}/products/{pid}",
            json={"is_available": False},
            headers=_auth(token),
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["is_available"] is False


@pytest.mark.asyncio
async def test_eliminar_producto_sin_pedidos() -> None:
    """Un producto sin pedidos se elimina físicamente."""
    async with await _make_client() as client:
        token, cid = await _setup(client)
        resp = await client.post(
            f"/comercios/{cid}/products",
            json={"code": "EMP-POL", "short_name": "Pollo", "full_name": "Empanada de Pollo", "category": "empanada"},
            headers=_auth(token),
        )
        assert resp.status_code == 201
        pid = resp.json()["id"]

        del_resp = await client.delete(f"/comercios/{cid}/products/{pid}", headers=_auth(token))
        assert del_resp.status_code == 204

        # Ya no existe
        get_resp = await client.get(f"/comercios/{cid}/products/{pid}", headers=_auth(token))
        assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_aislamiento_tenant() -> None:
    """Un usuario no puede ver los productos de otro comercio."""
    async with await _make_client() as client:
        token_a, cid_a = await _setup(client)

        # Dueño B con su propio comercio
        resp_b = await client.post(
            "/auth/registro",
            json={"name": "B", "email": _email("b"), "password": "password123", "account_type": "owner"},
        )
        token_b = resp_b.json()["token"]["access_token"]

        # B intenta listar productos del comercio de A
        resp = await client.get(f"/comercios/{cid_a}/products", headers=_auth(token_b))
        assert resp.status_code == 403


# ── Catálogo (precios) ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_crear_precios_pizza() -> None:
    """Se pueden asignar precio grande y chica a una pizza."""
    async with await _make_client() as client:
        token, cid = await _setup(client)
        # Crear producto
        p_resp = await client.post(
            f"/comercios/{cid}/products",
            json={"code": "PIZ-MOZ2", "short_name": "Mozza2", "full_name": "Pizza Mozzarella 2", "category": "pizza"},
            headers=_auth(token),
        )
        pid = p_resp.json()["id"]

        # Asignar precios
        c_resp = await client.post(
            f"/comercios/{cid}/catalog",
            json={"product_id": pid, "price_large": 2100.0, "price_small": 1400.0},
            headers=_auth(token),
        )
        assert c_resp.status_code == 201
        data = c_resp.json()
        assert float(data["price_large"]) == 2100.0
        assert float(data["price_small"]) == 1400.0


@pytest.mark.asyncio
async def test_crear_precios_empanada() -> None:
    """Se pueden asignar precio unitario y por docena a una empanada."""
    async with await _make_client() as client:
        token, cid = await _setup(client)
        p_resp = await client.post(
            f"/comercios/{cid}/products",
            json={"code": "EMP-JAQ", "short_name": "J y Q", "full_name": "Jamón y Queso", "category": "empanada"},
            headers=_auth(token),
        )
        pid = p_resp.json()["id"]

        c_resp = await client.post(
            f"/comercios/{cid}/catalog",
            json={"product_id": pid, "price_unit": 300.0, "price_dozen": 3200.0},
            headers=_auth(token),
        )
        assert c_resp.status_code == 201
        data = c_resp.json()
        assert float(data["price_unit"]) == 300.0
        assert float(data["price_dozen"]) == 3200.0


# ── Combos ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_crear_combo_ok() -> None:
    """Se puede crear un combo con productos del comercio."""
    async with await _make_client() as client:
        token, cid = await _setup(client)
        headers = _auth(token)

        # Crear productos
        p1 = await client.post(
            f"/comercios/{cid}/products",
            json={"code": "PIZ-C1", "short_name": "Pizza C1", "full_name": "Pizza C1", "category": "pizza"},
            headers=headers,
        )
        p2 = await client.post(
            f"/comercios/{cid}/products",
            json={"code": "BEB-C1", "short_name": "Bebida C1", "full_name": "Bebida C1", "category": "drink"},
            headers=headers,
        )
        pid1 = p1.json()["id"]
        pid2 = p2.json()["id"]

        resp = await client.post(
            f"/comercios/{cid}/combos",
            json={
                "code": "CMB-FAM",
                "short_name": "Familiar",
                "full_name": "Combo Familiar",
                "price": 3500.0,
                "items": [
                    {"product_id": pid1, "quantity": 1},
                    {"product_id": pid2, "quantity": 2},
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == "CMB-FAM"
        assert float(data["price"]) == 3500.0
        assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_editar_combo_reemplaza_items() -> None:
    """Al editar un combo enviando items, se reemplazan los anteriores."""
    async with await _make_client() as client:
        token, cid = await _setup(client)
        headers = _auth(token)

        p1 = await client.post(
            f"/comercios/{cid}/products",
            json={"code": "PIZ-E1", "short_name": "P1", "full_name": "Producto 1", "category": "pizza"},
            headers=headers,
        )
        p2 = await client.post(
            f"/comercios/{cid}/products",
            json={"code": "PIZ-E2", "short_name": "P2", "full_name": "Producto 2", "category": "pizza"},
            headers=headers,
        )
        pid1 = p1.json()["id"]
        pid2 = p2.json()["id"]

        create_resp = await client.post(
            f"/comercios/{cid}/combos",
            json={
                "code": "CMB-NOCHE",
                "short_name": "Noche",
                "full_name": "Combo Noche",
                "price": 2800.0,
                "items": [{"product_id": pid1, "quantity": 1}],
            },
            headers=headers,
        )
        combo_id = create_resp.json()["id"]

        # Editar: reemplazar items por p2
        edit_resp = await client.patch(
            f"/comercios/{cid}/combos/{combo_id}",
            json={"items": [{"product_id": pid2, "quantity": 3}]},
            headers=headers,
        )
        assert edit_resp.status_code == 200
        data = edit_resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["product_id"] == pid2
        assert data["items"][0]["quantity"] == 3


@pytest.mark.asyncio
async def test_combo_codigo_duplicado_409() -> None:
    """No se puede crear dos combos con el mismo código en el mismo comercio."""
    async with await _make_client() as client:
        token, cid = await _setup(client)
        headers = _auth(token)
        payload = {
            "code": "CMB-DUP",
            "short_name": "Dup",
            "full_name": "Combo Duplicado",
            "price": 1000.0,
        }
        r1 = await client.post(f"/comercios/{cid}/combos", json=payload, headers=headers)
        assert r1.status_code == 201
        r2 = await client.post(f"/comercios/{cid}/combos", json=payload, headers=headers)
        assert r2.status_code == 409


@pytest.mark.asyncio
async def test_eliminar_combo_sin_pedidos() -> None:
    """Un combo sin pedidos se elimina físicamente."""
    async with await _make_client() as client:
        token, cid = await _setup(client)
        resp = await client.post(
            f"/comercios/{cid}/combos",
            json={"code": "CMB-DEL", "short_name": "Del", "full_name": "Combo a Eliminar", "price": 500.0},
            headers=_auth(token),
        )
        assert resp.status_code == 201
        comb_id = resp.json()["id"]

        del_resp = await client.delete(f"/comercios/{cid}/combos/{comb_id}", headers=_auth(token))
        assert del_resp.status_code == 204

        get_resp = await client.get(f"/comercios/{cid}/combos/{comb_id}", headers=_auth(token))
        assert get_resp.status_code == 404
