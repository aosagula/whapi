from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.main import app
from app.models.account import Business
from app.models.catalog import CatalogItem, Combo, ComboItem, Product
from app.models.conversation import ConversationSession, Message
from app.models.customer import Customer
from app.models.order import Order, OrderItem


def _email(tag: str) -> str:
    return f"{tag}_{uuid.uuid4().hex[:8]}@test.com"


async def _register_and_create_business(client: AsyncClient, tag: str) -> dict:
    resp = await client.post(
        "/auth/registro",
        json={
            "name": f"User {tag}",
            "email": _email(tag),
            "password": "password123",
            "account_type": "owner",
        },
    )
    assert resp.status_code == 201
    token = resp.json()["token"]["access_token"]

    resp = await client.post(
        "/comercios",
        json={"name": f"Pizzeria {tag}"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_agent_infer_requires_api_key() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/agent/infer",
            json={
                "context": {
                    "business_id": str(uuid.uuid4()),
                    "session_id": str(uuid.uuid4()),
                    "latest_user_message": "Hola",
                    "stage": "general_query",
                }
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_agent_infer_returns_structured_decision() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/agent/infer",
            headers={"X-Agent-Api-Key": "agent-local-dev-key"},
            json={
                "context": {
                    "business_id": str(uuid.uuid4()),
                    "session_id": str(uuid.uuid4()),
                    "latest_user_message": "Hola, que pizzas tienen?",
                    "stage": "general_query",
                }
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["intent"] == "query_catalog"
    assert body["decision"]["stage"] == "general_query"
    assert "fetch_catalog" in body["decision"]["tool_actions"]


@pytest.mark.asyncio
async def test_agent_context_returns_business_customer_catalog_and_order() -> None:
    business_id: str
    phone = "5491157046954"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        business = await _register_and_create_business(client, "agent_ctx")
        business_id = business["id"]

    async with AsyncSessionLocal() as db:
        business_model = await db.get(Business, uuid.UUID(business_id))
        assert business_model is not None
        business_model.assistant_name = "Pia"
        business_model.assistant_system_prompt_master = "Sos el asistente principal del comercio."
        business_model.assistant_system_prompt_default = "Ayuda a cerrar pedidos sin inventar productos."
        business_model.half_half_surcharge = 700

        customer = Customer(
            business_id=business_model.id,
            phone=phone,
            name="Luciana Coccari",
            whatsapp_wa_id="238465945968878@c.us",
            whatsapp_display_name="Luciana Coccari",
            whatsapp_profile_name="Telefono Backup Vaclog",
            address="Corrientes 1234",
            credit_balance=250,
        )
        db.add(customer)
        await db.flush()

        session = ConversationSession(
            business_id=business_model.id,
            customer_id=customer.id,
            status="active_bot",
        )
        db.add(session)
        await db.flush()

        db.add_all(
            [
                Message(session_id=session.id, direction="inbound", content="Hola", sender_phone=phone, sender_name="Luciana Coccari"),
                Message(session_id=session.id, direction="outbound", content="Tenemos muzza y fugazza", sender_name="Pia"),
            ]
        )

        product = Product(
            business_id=business_model.id,
            code="PIZ-MOZ",
            short_name="Muzza",
            full_name="Pizza Muzza",
            category="pizza",
            is_available=True,
        )
        db.add(product)
        await db.flush()
        db.add(
            CatalogItem(
                business_id=business_model.id,
                product_id=product.id,
                price_large=12000,
                price_small=9000,
                is_available=True,
            )
        )

        combo = Combo(
            business_id=business_model.id,
            code="COMBO1",
            short_name="Combo 1",
            full_name="Combo Familiar",
            price=18500,
            is_available=True,
        )
        db.add(combo)
        await db.flush()
        db.add(ComboItem(combo_id=combo.id, product_id=product.id, quantity=1, is_open=False))

        order = Order(
            business_id=business_model.id,
            order_number=1,
            customer_id=customer.id,
            session_id=session.id,
            status="in_progress",
            payment_status="no_charge",
            origin="whatsapp",
            delivery_type="delivery",
            delivery_address="Corrientes 1234 entre Callao y Riobamba",
            total_amount=12000,
            credit_applied=0,
        )
        db.add(order)
        await db.flush()
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=1,
                unit_price=12000,
                variant={"size": "large"},
                notes="Sin aceitunas",
            )
        )
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/agent/businesses/{business_id}/context",
            params={"phone": f"+{phone}@c.us"},
            headers={"X-Agent-Api-Key": "agent-local-dev-key"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["assistant"]["name"] == "Pia"
    assert "No inventar productos" in body["assistant"]["effective_system_prompt"]
    assert body["customer"]["name"] == "Luciana Coccari"
    assert body["customer"]["phone"] == phone
    assert body["customer"]["whatsapp_wa_id"] == "238465945968878@c.us"
    assert len(body["recent_messages"]) == 2
    assert body["active_order"]["delivery_type"] == "delivery"
    assert body["active_order"]["items"][0]["product_name"] == "Pizza Muzza"
    assert len(body["catalog"]["products"]) == 1
    assert len(body["catalog"]["combos"]) == 1
    assert body["rules"]["half_half_surcharge"] == 700.0


@pytest.mark.asyncio
async def test_agent_context_creates_customer_and_session_when_missing() -> None:
    phone = "5491112233445"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        business = await _register_and_create_business(client, "agent_ctx_new")
        response = await client.get(
            f"/agent/businesses/{business['id']}/context",
            params={"phone": phone},
            headers={"X-Agent-Api-Key": "agent-local-dev-key"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["customer"]["phone"] == phone
    assert body["session_status"] == "active_bot"
    assert body["active_order"] is None
    assert body["recent_messages"] == []

    async with AsyncSessionLocal() as db:
        customer_result = await db.execute(
            select(Customer).where(
                Customer.business_id == uuid.UUID(business["id"]),
                Customer.phone == phone,
            )
        )
        session_result = await db.execute(
            select(ConversationSession).where(ConversationSession.business_id == uuid.UUID(business["id"]))
        )
        assert customer_result.scalar_one_or_none() is not None
        assert session_result.scalar_one_or_none() is not None
