"""Endpoints internos para inferencia controlada del agente."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import settings
from app.schemas.agent import AgentInferenceRequest, AgentInferenceResponse
from app.services.agent_orchestrator import infer_agent_turn

router = APIRouter(prefix="/agent", tags=["agent"])


def _verify_agent_api_key(x_agent_api_key: str = Header(..., alias="X-Agent-Api-Key")) -> None:
    expected = settings.AGENT_API_KEY or settings.N8N_API_KEY
    if not expected or x_agent_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Agent-Api-Key inválida",
        )


@router.post("/infer", response_model=AgentInferenceResponse)
async def infer(request: AgentInferenceRequest, x_agent_api_key: str = Header(..., alias="X-Agent-Api-Key")) -> AgentInferenceResponse:
    """Recibe contexto estructurado y devuelve una decisión estructurada del agente."""
    _verify_agent_api_key(x_agent_api_key)

    if not settings.AGENT_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El agente local está deshabilitado",
        )

    return await infer_agent_turn(request.context)
