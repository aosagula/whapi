"""Schemas estructurados para la capa de orquestación del agente."""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


AgentIntent = Literal[
    "query_catalog",
    "query_price",
    "query_order_status",
    "start_order",
    "update_order",
    "confirm_order",
    "select_delivery_type",
    "select_payment_method",
    "send_transfer_receipt",
    "request_human",
    "unsupported",
]

AgentStage = Literal[
    "general_query",
    "building_order",
    "confirming_delivery",
    "confirming_payment",
    "awaiting_transfer_receipt",
    "confirmed",
    "human_handoff",
]

AgentToolAction = Literal[
    "none",
    "fetch_catalog",
    "create_draft_order",
    "update_draft_order",
    "recalculate_total",
    "generate_payment_link",
    "send_transfer_instructions",
    "handoff_to_human",
]


class AgentTurnContext(BaseModel):
    business_id: uuid.UUID
    session_id: uuid.UUID
    customer_id: uuid.UUID | None = None
    stage: AgentStage = "general_query"
    latest_user_message: str = ""
    customer_name: str | None = None
    catalog_summary: list[str] = Field(default_factory=list)
    order_summary: str | None = None
    total_amount: float | None = None
    delivery_type: str | None = None
    payment_method: str | None = None


class AgentDecision(BaseModel):
    intent: AgentIntent
    stage: AgentStage
    reply_messages: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    tool_actions: list[AgentToolAction] = Field(default_factory=list)
    requires_human: bool = False
    notes: str | None = None


class AgentInferenceRequest(BaseModel):
    context: AgentTurnContext


class AgentInferenceResponse(BaseModel):
    decision: AgentDecision
