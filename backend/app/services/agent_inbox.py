"""Flujo de entrada de mensajes hacia el agente conversacional."""
from __future__ import annotations

import logging
from textwrap import shorten

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import ConversationSession, Message
from app.models.customer import Customer
from app.models.whatsapp import WhatsappNumber
from app.schemas.agent import AgentSessionState, AgentTurnContext
from app.services.agent_context import build_agent_context
from app.services.agent_orchestrator import infer_agent_turn
from app.services.notificaciones import enviar_mensaje_whatsapp
from app.services.agent_state import update_agent_session_state

logger = logging.getLogger(__name__)


async def process_incoming_agent_message(
    db: AsyncSession,
    session: ConversationSession,
    customer: Customer,
    whatsapp_number: WhatsappNumber,
    latest_user_message: str,
) -> dict | None:
    """Procesa un inbound con el agente cuando la sesion sigue a cargo del bot."""
    if not latest_user_message.strip():
        logger.info("Agent inbox omitido: mensaje vacio para sesion=%s", session.id)
        return None

    if session.status != "active_bot":
        logger.info("Agent inbox omitido: sesion=%s en estado=%s", session.id, session.status)
        return None

    context = await build_agent_context(
        db=db,
        business_id=session.business_id,
        phone=customer.phone or customer.whatsapp_wa_id or "",
        recent_messages_limit=20,
    )
    logger.info(
        "Agent inbox context sesion=%s customer=%s stage=%s catalog_items=%s combos=%s recent_messages=%s prompt_preview=%s",
        session.id,
        context.customer.customer_id,
        context.agent_state.stage,
        len(context.catalog.products),
        len(context.catalog.combos),
        len(context.recent_messages),
        shorten(context.assistant.effective_system_prompt.replace("\n", " "), width=240, placeholder="..."),
    )
    logger.info(
        "Agent inbox nota: orchestrator=%s usa logica heuristica; el prompt se carga pero todavia no se envia al modelo local.",
        "state_machine",
    )

    turn_context = AgentTurnContext(
        business_id=context.business_id,
        session_id=context.session_id,
        customer_id=context.customer.customer_id,
        stage=context.agent_state.stage,
        latest_user_message=latest_user_message,
        customer_name=context.customer.name or context.customer.whatsapp_display_name or context.customer.whatsapp_profile_name,
        catalog_summary=context.catalog.summary,
        order_summary=context.active_order.summary if context.active_order else None,
        total_amount=context.active_order.total_amount if context.active_order else None,
        delivery_type=context.active_order.delivery_type if context.active_order else None,
        payment_method=context.agent_state.metadata.get("payment_method") if isinstance(context.agent_state.metadata, dict) else None,
    )
    logger.info(
        "Agent inbox turn_context sesion=%s stage=%s latest_user_message=%r order_summary=%r total_amount=%s delivery_type=%s payment_method=%s",
        session.id,
        turn_context.stage,
        latest_user_message,
        turn_context.order_summary,
        turn_context.total_amount,
        turn_context.delivery_type,
        turn_context.payment_method,
    )

    inference = await infer_agent_turn(turn_context)
    decision = inference.decision
    logger.info(
        "Agent inbox decision sesion=%s intent=%s next_stage=%s missing_fields=%s tool_actions=%s requires_human=%s notes=%r",
        session.id,
        decision.intent,
        decision.stage,
        decision.missing_fields,
        decision.tool_actions,
        decision.requires_human,
        decision.notes,
    )

    next_state = AgentSessionState(
        stage=decision.stage,
        current_intent=decision.intent,
        missing_fields=decision.missing_fields,
        last_summary=context.active_order.summary if context.active_order else None,
        last_user_message=latest_user_message,
        requires_human=decision.requires_human,
        draft_order_id=context.active_order.order_id if context.active_order else None,
        active_order_id=context.active_order.order_id if context.active_order else None,
        metadata={"tool_actions": decision.tool_actions},
    )
    persisted_state = await update_agent_session_state(db=db, session_id=session.id, state=next_state)
    logger.info(
        "Agent inbox persisted_state sesion=%s stage=%s current_intent=%s metadata=%s",
        session.id,
        persisted_state.stage,
        persisted_state.current_intent,
        persisted_state.metadata,
    )

    if decision.requires_human:
        session.status = "waiting_operator"
        await db.commit()
        await db.refresh(session)

    reply_text = "\n\n".join(part.strip() for part in decision.reply_messages if part and part.strip())
    if not reply_text:
        logger.info("Agent inbox sin reply_messages para sesion=%s intent=%s", session.id, decision.intent)
        return {
            "decision": decision.model_dump(mode="json"),
            "agent_state": persisted_state.model_dump(mode="json"),
        }

    db.add(
        Message(
            session_id=session.id,
            direction="outbound",
            content=reply_text,
            sender_name=context.assistant.name,
        )
    )
    await db.commit()

    if whatsapp_number.session_name:
        await enviar_mensaje_whatsapp(
            customer.whatsapp_wa_id or customer.phone,
            reply_text,
            whatsapp_number.session_name,
            token=whatsapp_number.wpp_token,
        )

    logger.info(
        "Agent inbox respondio sesion=%s intent=%s stage=%s reply_text=%r",
        session.id,
        decision.intent,
        decision.stage,
        reply_text,
    )
    return {
        "decision": decision.model_dump(mode="json"),
        "agent_state": persisted_state.model_dump(mode="json"),
        "reply_text": reply_text,
    }
