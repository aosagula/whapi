"""Tests del endpoint /health — verifica que la API y la DB están operativas."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_returns_ok() -> None:
    """El endpoint /health debe responder con status 200 y {"status": "ok"}."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_db_connection() -> None:
    """El endpoint /health debe conectar a la base de datos sin lanzar excepciones."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    # Si la DB no conecta, FastAPI lanza un 500
    assert response.status_code != 500
