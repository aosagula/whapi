"""Schemas estructurados para la capa de orquestación del agente."""
from __future__ import annotations

import uuid
from datetime import datetime
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


class AgentAssistantContext(BaseModel):
    name: str
    system_prompt_master: str | None = None
    system_prompt_default: str | None = None
    effective_system_prompt: str


class AgentBusinessRulesContext(BaseModel):
    half_half_surcharge: float
    rules: list[str] = Field(default_factory=list)


class AgentCustomerContext(BaseModel):
    customer_id: uuid.UUID
    phone: str | None = None
    whatsapp_lid: str | None = None
    whatsapp_wa_id: str | None = None
    name: str | None = None
    whatsapp_display_name: str | None = None
    whatsapp_profile_name: str | None = None
    whatsapp_business_name: str | None = None
    address: str | None = None
    credit_balance: float
    has_whatsapp: bool


class AgentMessageContext(BaseModel):
    direction: str
    content: str
    sent_at: datetime
    sender_phone: str | None = None
    sender_name: str | None = None


class AgentCatalogProductContext(BaseModel):
    product_id: uuid.UUID
    code: str
    short_name: str
    full_name: str
    description: str | None = None
    category: str
    price_large: float | None = None
    price_small: float | None = None
    price_unit: float | None = None
    price_dozen: float | None = None


class AgentCatalogComboContext(BaseModel):
    combo_id: uuid.UUID
    code: str
    short_name: str
    full_name: str
    description: str | None = None
    price: float
    items_description: str


class AgentCatalogContext(BaseModel):
    products: list[AgentCatalogProductContext] = Field(default_factory=list)
    combos: list[AgentCatalogComboContext] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)


class AgentOrderItemContext(BaseModel):
    item_id: uuid.UUID
    product_id: uuid.UUID | None = None
    combo_id: uuid.UUID | None = None
    product_name: str | None = None
    quantity: int
    unit_price: float
    subtotal: float
    variant: dict | None = None
    notes: str | None = None


class AgentOrderContext(BaseModel):
    order_id: uuid.UUID
    order_number: int
    status: str
    payment_status: str
    delivery_type: str
    delivery_address: str | None = None
    total_amount: float
    credit_applied: float
    summary: str
    items: list[AgentOrderItemContext] = Field(default_factory=list)


class AgentResolvedContext(BaseModel):
    business_id: uuid.UUID
    business_name: str
    session_id: uuid.UUID
    session_status: str
    assistant: AgentAssistantContext
    customer: AgentCustomerContext
    active_order: AgentOrderContext | None = None
    recent_messages: list[AgentMessageContext] = Field(default_factory=list)
    catalog: AgentCatalogContext
    rules: AgentBusinessRulesContext
