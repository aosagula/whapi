"""Endpoints internos para inferencia y contexto controlado del agente."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.schemas.agent import (
    AgentInferenceRequest,
    AgentInferenceResponse,
    AgentResolvedContext,
    AgentSessionState,
)
from app.services.agent_context import build_agent_context
from app.services.agent_orchestrator import infer_agent_turn
from app.services.agent_state import get_agent_session_state, update_agent_session_state

router = APIRouter(prefix="/agent", tags=["agent"])


def _verify_agent_api_key(x_agent_api_key: str = Header(..., alias="X-Agent-Api-Key")) -> None:
    expected = settings.AGENT_API_KEY or settings.N8N_API_KEY
    if not expected or x_agent_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Agent-Api-Key invalida",
        )


@router.post("/infer", response_model=AgentInferenceResponse)
async def infer(
    request: AgentInferenceRequest,
    x_agent_api_key: str = Header(..., alias="X-Agent-Api-Key"),
) -> AgentInferenceResponse:
    """Recibe contexto estructurado y devuelve una decision estructurada del agente."""
    _verify_agent_api_key(x_agent_api_key)

    if not settings.AGENT_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El agente local esta deshabilitado",
        )

    return await infer_agent_turn(request.context)


@router.get("/businesses/{business_id}/context", response_model=AgentResolvedContext)
async def get_context(
    business_id: uuid.UUID,
    phone: str = Query(..., description="Telefono del cliente a resolver para el contexto"),
    recent_messages_limit: int = Query(20, ge=1, le=50),
    x_agent_api_key: str = Header(..., alias="X-Agent-Api-Key"),
    db: AsyncSession = Depends(get_db),
) -> AgentResolvedContext:
    """Construye el contexto completo del agente para un comercio y cliente."""
    _verify_agent_api_key(x_agent_api_key)
    return await build_agent_context(
        db=db,
        business_id=business_id,
        phone=phone,
        recent_messages_limit=recent_messages_limit,
    )


@router.get("/sessions/{session_id}/state", response_model=AgentSessionState)
async def get_session_state(
    session_id: uuid.UUID,
    x_agent_api_key: str = Header(..., alias="X-Agent-Api-Key"),
    db: AsyncSession = Depends(get_db),
) -> AgentSessionState:
    """Obtiene el estado conversacional persistido del agente para una sesion."""
    _verify_agent_api_key(x_agent_api_key)
    return await get_agent_session_state(db=db, session_id=session_id)


@router.patch("/sessions/{session_id}/state", response_model=AgentSessionState)
async def patch_session_state(
    session_id: uuid.UUID,
    state: AgentSessionState,
    x_agent_api_key: str = Header(..., alias="X-Agent-Api-Key"),
    db: AsyncSession = Depends(get_db),
) -> AgentSessionState:
    """Actualiza el estado conversacional persistido del agente para una sesion."""
    _verify_agent_api_key(x_agent_api_key)
    return await update_agent_session_state(db=db, session_id=session_id, state=state)
