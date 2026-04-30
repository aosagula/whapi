"""Capa de orquestacion del agente conversacional."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging

from app.core.config import settings
from app.schemas.agent import AgentDecision, AgentInferenceResponse, AgentStage, AgentTurnContext


StageHandler = Callable[[AgentTurnContext], Awaitable[AgentDecision]]
logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    return (text or "").strip().lower()


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


class StateMachineAgentOrchestrator:
    """Maquina de estados explicita para el flujo del agente."""

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
        logger.info(
            "Agent orchestrator run stage=%s latest_user_message=%r customer_name=%r catalog_summary_items=%s order_summary_present=%s",
            context.stage,
            context.latest_user_message,
            context.customer_name,
            len(context.catalog_summary),
            bool(context.order_summary),
        )
        handler = self._handlers.get(context.stage)
        if handler is None:
            logger.warning("Agent orchestrator stage no soportado: %s", context.stage)
            return AgentDecision(
                intent="unsupported",
                stage="human_handoff",
                reply_messages=[
                    "No pude determinar el estado de esta conversacion. Te derivo con una persona."
                ],
                tool_actions=["handoff_to_human"],
                requires_human=True,
                notes=f"stage no soportado: {context.stage}",
            )
        return await handler(context)

    async def _handle_general_query(self, context: AgentTurnContext) -> AgentDecision:
        text = _normalize_text(context.latest_user_message)
        logger.info("Agent orchestrator general_query normalized_text=%r", text)

        if _contains_any(text, ("humano", "persona", "operador", "asesor")):
            logger.info("Agent orchestrator branch=human_handoff")
            return AgentDecision(
                intent="request_human",
                stage="human_handoff",
                reply_messages=["Te derivo con una persona para continuar."],
                tool_actions=["handoff_to_human"],
                requires_human=True,
            )

        if _contains_any(text, ("estado", "pedido", "demora", "llega", "envio")):
            logger.info("Agent orchestrator branch=query_order_status has_order=%s", bool(context.order_summary))
            if context.order_summary:
                return AgentDecision(
                    intent="query_order_status",
                    stage="general_query",
                    reply_messages=[f"Tu pedido actual es: {context.order_summary}"],
                    tool_actions=["none"],
                )
            return AgentDecision(
                intent="query_order_status",
                stage="general_query",
                reply_messages=["No veo un pedido en curso. Si queres, te ayudo a armar uno nuevo."],
                tool_actions=["none"],
            )

        if _contains_any(text, ("quiero", "pedido", "pedir", "comprar", "encargar")):
            logger.info("Agent orchestrator branch=start_order")
            return AgentDecision(
                intent="start_order",
                stage="building_order",
                reply_messages=[
                    "Perfecto. Decime que productos queres, con tamano y cantidad, y te ayudo a armar el pedido."
                ],
                tool_actions=["create_draft_order", "fetch_catalog"],
            )

        catalog_lines = context.catalog_summary[:5]
        if catalog_lines:
            logger.info("Agent orchestrator branch=query_catalog catalog_lines=%s", len(catalog_lines))
            catalog_text = "\n".join(f"- {line}" for line in catalog_lines)
            return AgentDecision(
                intent="query_catalog",
                stage="general_query",
                reply_messages=[
                    "Estas son algunas opciones disponibles:",
                    catalog_text,
                    "Si queres comprar, decime producto y cantidad.",
                ],
                tool_actions=["fetch_catalog"],
                notes=f"orquestacion base preparada para mensaje: {context.latest_user_message!r}",
            )

        logger.info("Agent orchestrator branch=query_catalog_fallback_without_catalog")
        return AgentDecision(
            intent="query_catalog",
            stage="general_query",
            reply_messages=["Contame que te gustaria pedir y te ayudo con las opciones disponibles."],
            tool_actions=["fetch_catalog"],
        )

    async def _handle_building_order(self, context: AgentTurnContext) -> AgentDecision:
        text = _normalize_text(context.latest_user_message)
        logger.info("Agent orchestrator building_order normalized_text=%r", text)
        if _contains_any(text, ("eso es todo", "listo", "confirmo", "nada mas")):
            logger.info("Agent orchestrator branch=confirming_delivery")
            return AgentDecision(
                intent="confirm_order",
                stage="confirming_delivery",
                reply_messages=[
                    "Perfecto. Decime si retiras por el local o si es con delivery."
                ],
                tool_actions=["recalculate_total"],
            )
        logger.info("Agent orchestrator branch=update_order")
        return AgentDecision(
            intent="update_order",
            stage="building_order",
            reply_messages=[
                "Sigo armando tu pedido. Decime producto, tamano, gustos y cantidad de cada item."
            ],
            tool_actions=["update_draft_order", "recalculate_total"],
        )

    async def _handle_confirming_delivery(self, context: AgentTurnContext) -> AgentDecision:
        text = _normalize_text(context.latest_user_message)
        logger.info("Agent orchestrator confirming_delivery normalized_text=%r", text)
        if _contains_any(text, ("retiro", "retirar", "paso a buscar", "buscar")):
            logger.info("Agent orchestrator branch=pickup")
            return AgentDecision(
                intent="select_delivery_type",
                stage="confirming_payment",
                reply_messages=["Perfecto, retiro por local. Ahora decime si pagas en efectivo, transferencia o Mercado Pago."],
                missing_fields=["payment_method"],
                tool_actions=["none"],
            )
        if _contains_any(text, ("delivery", "enviar", "envio", "mandar")):
            logger.info("Agent orchestrator branch=delivery_missing_address")
            return AgentDecision(
                intent="select_delivery_type",
                stage="confirming_delivery",
                reply_messages=["Perfecto, es con delivery. Pasame calle, numero y entre calles para seguir."],
                missing_fields=["street", "door_number", "cross_streets"],
                tool_actions=["none"],
            )
        logger.info("Agent orchestrator branch=delivery_type_missing")
        return AgentDecision(
            intent="select_delivery_type",
            stage="confirming_delivery",
            reply_messages=["Necesito que me indiques si retiras por el local o si lo enviamos por delivery."],
            missing_fields=["delivery_type"],
            tool_actions=["none"],
        )

    async def _handle_confirming_payment(self, context: AgentTurnContext) -> AgentDecision:
        text = _normalize_text(context.latest_user_message)
        logger.info("Agent orchestrator confirming_payment normalized_text=%r", text)
        if _contains_any(text, ("efectivo",)):
            logger.info("Agent orchestrator branch=payment_cash")
            return AgentDecision(
                intent="select_payment_method",
                stage="confirmed",
                reply_messages=["Perfecto, queda registrado pago en efectivo. En el siguiente paso te voy a confirmar el pedido completo."],
                tool_actions=["none"],
            )
        if _contains_any(text, ("transferencia", "transferir")):
            logger.info("Agent orchestrator branch=payment_transfer")
            return AgentDecision(
                intent="select_payment_method",
                stage="awaiting_transfer_receipt",
                reply_messages=["Perfecto, seguimos por transferencia. En el siguiente paso te voy a enviar los datos y quedar a la espera del comprobante."],
                tool_actions=["send_transfer_instructions"],
            )
        if _contains_any(text, ("mercado pago", "mercadopago", "mp")):
            logger.info("Agent orchestrator branch=payment_mp")
            return AgentDecision(
                intent="select_payment_method",
                stage="confirmed",
                reply_messages=["Perfecto, seguimos con Mercado Pago. En el siguiente paso te voy a generar el link de pago."],
                tool_actions=["generate_payment_link"],
            )
        logger.info("Agent orchestrator branch=payment_method_missing")
        return AgentDecision(
            intent="select_payment_method",
            stage="confirming_payment",
            reply_messages=["Decime si pagas en efectivo, transferencia o Mercado Pago."],
            missing_fields=["payment_method"],
            tool_actions=["none"],
        )

    async def _handle_awaiting_transfer_receipt(self, context: AgentTurnContext) -> AgentDecision:
        logger.info("Agent orchestrator awaiting_transfer_receipt")
        return AgentDecision(
            intent="send_transfer_receipt",
            stage="awaiting_transfer_receipt",
            reply_messages=["Quedo a la espera del comprobante para que una persona lo revise."],
            tool_actions=["none"],
            requires_human=True,
        )

    async def _handle_confirmed(self, context: AgentTurnContext) -> AgentDecision:
        logger.info("Agent orchestrator confirmed")
        return AgentDecision(
            intent="confirm_order",
            stage="confirmed",
            reply_messages=["Perfecto. Estoy terminando de confirmar tu pedido."],
            tool_actions=["none"],
        )

    async def _handle_human_handoff(self, context: AgentTurnContext) -> AgentDecision:
        logger.info("Agent orchestrator human_handoff")
        return AgentDecision(
            intent="request_human",
            stage="human_handoff",
            reply_messages=["Te derivo con una persona para continuar."],
            tool_actions=["handoff_to_human"],
            requires_human=True,
        )


def get_agent_orchestrator() -> StateMachineAgentOrchestrator:
    """Factory central de la capa de orquestacion."""
    orchestrator = settings.AGENT_ORCHESTRATOR.strip().lower()
    if orchestrator != "state_machine":
        raise ValueError(f"Orquestador no soportado: {settings.AGENT_ORCHESTRATOR}")
    return StateMachineAgentOrchestrator()


async def infer_agent_turn(context: AgentTurnContext) -> AgentInferenceResponse:
    """Ejecuta un turno de inferencia controlada usando el orquestador configurado."""
    orchestrator = get_agent_orchestrator()
    logger.info(
        "Agent infer start orchestrator=%s stage=%s latest_user_message=%r",
        settings.AGENT_ORCHESTRATOR,
        context.stage,
        context.latest_user_message,
    )
    decision = await orchestrator.run(context)
    logger.info(
        "Agent infer end intent=%s next_stage=%s reply_count=%s",
        decision.intent,
        decision.stage,
        len(decision.reply_messages),
    )
    return AgentInferenceResponse(decision=decision)
