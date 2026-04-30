"""Capa de orquestación del agente conversacional."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.core.config import settings
from app.schemas.agent import AgentDecision, AgentInferenceResponse, AgentStage, AgentTurnContext


StageHandler = Callable[[AgentTurnContext], Awaitable[AgentDecision]]


class StateMachineAgentOrchestrator:
    """Máquina de estados explícita para el flujo del agente."""

    def __init__(self) -> None:
        self._handlers: dict[AgentStage, StageHandler] = {
            "general_query": self._handle_general_query,
            "building_order": self._handle_building_order,
            "confirming_delivery": self._handle_confirming_delivery,
            "confirming_payment": self._handle_confirming_payment,
            "awaiting_transfer_receipt": self._handle_awaiting_transfer_receipt,
            "confirmed": self._handle_confirmed,
            "human_handoff": self._handle_human_handoff,
        }

    async def run(self, context: AgentTurnContext) -> AgentDecision:
        handler = self._handlers.get(context.stage)
        if handler is None:
            return AgentDecision(
                intent="unsupported",
                stage="human_handoff",
                reply_messages=[
                    "No pude determinar el estado de esta conversación. Te derivo con una persona."
                ],
                tool_actions=["handoff_to_human"],
                requires_human=True,
                notes=f"stage no soportado: {context.stage}",
            )
        return await handler(context)

    async def _handle_general_query(self, context: AgentTurnContext) -> AgentDecision:
        return AgentDecision(
            intent="query_catalog",
            stage="general_query",
            reply_messages=[],
            tool_actions=["fetch_catalog"],
            notes=f"orquestación base preparada para mensaje: {context.latest_user_message!r}",
        )

    async def _handle_building_order(self, context: AgentTurnContext) -> AgentDecision:
        return AgentDecision(
            intent="update_order",
            stage="building_order",
            reply_messages=[],
            tool_actions=["update_draft_order", "recalculate_total"],
        )

    async def _handle_confirming_delivery(self, context: AgentTurnContext) -> AgentDecision:
        return AgentDecision(
            intent="select_delivery_type",
            stage="confirming_delivery",
            reply_messages=[],
            missing_fields=["delivery_type", "delivery_address"],
            tool_actions=["none"],
        )

    async def _handle_confirming_payment(self, context: AgentTurnContext) -> AgentDecision:
        return AgentDecision(
            intent="select_payment_method",
            stage="confirming_payment",
            reply_messages=[],
            missing_fields=["payment_method"],
            tool_actions=["none"],
        )

    async def _handle_awaiting_transfer_receipt(self, context: AgentTurnContext) -> AgentDecision:
        return AgentDecision(
            intent="send_transfer_receipt",
            stage="awaiting_transfer_receipt",
            reply_messages=[],
            tool_actions=["none"],
        )

    async def _handle_confirmed(self, context: AgentTurnContext) -> AgentDecision:
        return AgentDecision(
            intent="confirm_order",
            stage="confirmed",
            reply_messages=[],
            tool_actions=["none"],
        )

    async def _handle_human_handoff(self, context: AgentTurnContext) -> AgentDecision:
        return AgentDecision(
            intent="request_human",
            stage="human_handoff",
            reply_messages=[],
            tool_actions=["handoff_to_human"],
            requires_human=True,
        )


def get_agent_orchestrator() -> StateMachineAgentOrchestrator:
    """Factory central de la capa de orquestación."""
    orchestrator = settings.AGENT_ORCHESTRATOR.strip().lower()
    if orchestrator != "state_machine":
        raise ValueError(f"Orquestador no soportado: {settings.AGENT_ORCHESTRATOR}")
    return StateMachineAgentOrchestrator()


async def infer_agent_turn(context: AgentTurnContext) -> AgentInferenceResponse:
    """Ejecuta un turno de inferencia controlada usando el orquestador configurado."""
    orchestrator = get_agent_orchestrator()
    decision = await orchestrator.run(context)
    return AgentInferenceResponse(decision=decision)
