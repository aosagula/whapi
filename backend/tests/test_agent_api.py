from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


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
                    "latest_user_message": "Hola, qué pizzas tienen?",
                    "stage": "general_query",
                }
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["intent"] == "query_catalog"
    assert body["decision"]["stage"] == "general_query"
    assert "fetch_catalog" in body["decision"]["tool_actions"]
