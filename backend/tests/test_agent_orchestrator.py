from __future__ import annotations

import uuid

import pytest

from app.schemas.agent import AgentTurnContext
from app.services.agent_orchestrator import get_agent_orchestrator


@pytest.mark.asyncio
async def test_state_machine_orchestrator_returns_catalog_action_for_general_query() -> None:
    orchestrator = get_agent_orchestrator()
    context = AgentTurnContext(
        business_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        latest_user_message="Hola, qué pizzas tienen?",
        stage="general_query",
    )

    decision = await orchestrator.run(context)

    assert decision.intent == "query_catalog"
    assert decision.stage == "general_query"
    assert "fetch_catalog" in decision.tool_actions
    assert decision.requires_human is False
