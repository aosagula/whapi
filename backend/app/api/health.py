from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.services.agent_runtime import get_agent_runtime_status

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Verifica que la API y la base de datos están operativas."""
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/health/agent")
async def health_agent() -> dict:
    """Retorna el estado básico del runtime local del agente."""
    status = await get_agent_runtime_status()
    return status.to_dict()
