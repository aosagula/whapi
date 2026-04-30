from __future__ import annotations

from dataclasses import asdict, dataclass

import httpx

from app.core.config import settings


@dataclass
class AgentRuntimeStatus:
    enabled: bool
    orchestrator: str
    provider: str
    model: str
    base_url: str
    reachable: bool
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


async def get_agent_runtime_status() -> AgentRuntimeStatus:
    """Retorna el estado básico del runtime local del agente."""
    if not settings.AGENT_ENABLED:
        return AgentRuntimeStatus(
            enabled=False,
            orchestrator=settings.AGENT_ORCHESTRATOR,
            provider=settings.LOCAL_LLM_PROVIDER,
            model=settings.LOCAL_LLM_MODEL,
            base_url=settings.LOCAL_LLM_BASE_URL,
            reachable=False,
            detail="agent disabled",
        )

    health_url = settings.LOCAL_LLM_BASE_URL.rstrip("/") + settings.LOCAL_LLM_HEALTH_PATH
    try:
        async with httpx.AsyncClient(timeout=settings.LOCAL_LLM_TIMEOUT_SECONDS) as client:
            response = await client.get(health_url)
            response.raise_for_status()
        return AgentRuntimeStatus(
            enabled=True,
            orchestrator=settings.AGENT_ORCHESTRATOR,
            provider=settings.LOCAL_LLM_PROVIDER,
            model=settings.LOCAL_LLM_MODEL,
            base_url=settings.LOCAL_LLM_BASE_URL,
            reachable=True,
            detail="runtime reachable",
        )
    except Exception as exc:  # noqa: BLE001
        return AgentRuntimeStatus(
            enabled=True,
            orchestrator=settings.AGENT_ORCHESTRATOR,
            provider=settings.LOCAL_LLM_PROVIDER,
            model=settings.LOCAL_LLM_MODEL,
            base_url=settings.LOCAL_LLM_BASE_URL,
            reachable=False,
            detail=str(exc),
        )
