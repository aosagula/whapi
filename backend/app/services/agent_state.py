"""Persistencia del estado conversacional del agente."""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import ConversationSession
from app.schemas.agent import AgentSessionState


async def get_agent_session_state(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> AgentSessionState:
    result = await db.execute(select(ConversationSession).where(ConversationSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Sesion no encontrada")
    raw_state = session.agent_state or {}
    return AgentSessionState.model_validate(raw_state) if raw_state else AgentSessionState()


async def update_agent_session_state(
    db: AsyncSession,
    session_id: uuid.UUID,
    state: AgentSessionState,
) -> AgentSessionState:
    result = await db.execute(select(ConversationSession).where(ConversationSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Sesion no encontrada")

    session.agent_state = state.model_dump(mode="json")
    await db.commit()
    await db.refresh(session)
    return AgentSessionState.model_validate(session.agent_state or {})
