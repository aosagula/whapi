"""Construcci\u00f3n del contexto estructurado del agente por comercio."""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Business
from app.models.catalog import CatalogItem, Combo, ComboItem, Product
from app.models.conversation import ConversationSession, Message
from app.models.customer import Customer
from app.models.order import Order
from app.schemas.agent import (
    AgentAssistantContext,
    AgentBusinessRulesContext,
    AgentCatalogComboContext,
    AgentCatalogContext,
    AgentCatalogProductContext,
    AgentCustomerContext,
    AgentMessageContext,
    AgentOrderContext,
    AgentOrderItemContext,
    AgentResolvedContext,
    AgentSessionState,
)


def _normalize_phone(value: str) -> str:
    return value.replace("@c.us", "").replace("@s.whatsapp.net", "").split("@")[0].lstrip("+").strip()


def _to_float(value: object | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _looks_like_lid(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.lower()
    return lowered.endswith("@lid") or lowered.endswith("@lid)")


def _extract_whatsapp_lid(customer: Customer) -> str | None:
    if _looks_like_lid(customer.whatsapp_wa_id):
        return customer.whatsapp_wa_id
    metadata = customer.whatsapp_metadata or {}
    for candidate in (
        metadata.get("sender", {}).get("id"),
        metadata.get("from"),
        metadata.get("wa_id"),
    ):
        if isinstance(candidate, str) and _looks_like_lid(candidate):
            return candidate
    return None


async def _get_business_or_404(db: AsyncSession, business_id: uuid.UUID) -> Business:
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    if business is None:
        raise HTTPException(status_code=404, detail="Comercio no encontrado")
    return business


async def _get_or_create_customer(db: AsyncSession, business_id: uuid.UUID, phone: str) -> Customer:
    result = await db.execute(
        select(Customer).where(
            Customer.business_id == business_id,
            Customer.phone == phone,
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        customer = Customer(business_id=business_id, phone=phone)
        db.add(customer)
        await db.flush()
    return customer


async def _get_or_create_session(db: AsyncSession, business_id: uuid.UUID, customer_id: uuid.UUID) -> ConversationSession:
    result = await db.execute(
        select(ConversationSession)
        .where(
            ConversationSession.business_id == business_id,
            ConversationSession.customer_id == customer_id,
            ConversationSession.status != "closed",
        )
        .order_by(ConversationSession.updated_at.desc())
        .limit(1)
    )
    session = result.scalar_one_or_none()
    if session is None:
        session = ConversationSession(
            business_id=business_id,
            customer_id=customer_id,
            status="active_bot",
        )
        db.add(session)
        await db.flush()
    return session


async def _get_active_order(db: AsyncSession, business_id: uuid.UUID, customer_id: uuid.UUID) -> Order | None:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(
            Order.business_id == business_id,
            Order.customer_id == customer_id,
            Order.status == "in_progress",
        )
        .order_by(Order.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _resolve_order_item_name(db: AsyncSession, item: object) -> str | None:
    product_id = getattr(item, "product_id", None)
    combo_id = getattr(item, "combo_id", None)
    if product_id:
        result = await db.execute(select(Product.full_name).where(Product.id == product_id))
        return result.scalar_one_or_none()
    if combo_id:
        result = await db.execute(select(Combo.full_name).where(Combo.id == combo_id))
        return result.scalar_one_or_none()
    return None


async def _build_order_context(db: AsyncSession, order: Order | None) -> AgentOrderContext | None:
    if order is None:
        return None

    items: list[AgentOrderItemContext] = []
    summary_parts: list[str] = []
    for item in order.items:
        product_name = await _resolve_order_item_name(db, item)
        subtotal = float(item.unit_price) * item.quantity
        items.append(
            AgentOrderItemContext(
                item_id=item.id,
                product_id=item.product_id,
                combo_id=item.combo_id,
                product_name=product_name,
                quantity=item.quantity,
                unit_price=float(item.unit_price),
                subtotal=subtotal,
                variant=item.variant,
                notes=item.notes,
            )
        )
        display_name = product_name or "Item sin nombre"
        summary_parts.append(f"{item.quantity}x {display_name} (${subtotal:.2f})")

    summary = ", ".join(summary_parts) if summary_parts else "Pedido borrador sin items."
    return AgentOrderContext(
        order_id=order.id,
        order_number=order.order_number,
        status=order.status,
        payment_status=order.payment_status,
        delivery_type=order.delivery_type,
        delivery_address=order.delivery_address,
        total_amount=float(order.total_amount),
        credit_applied=float(order.credit_applied),
        summary=summary,
        items=items,
    )


async def _build_catalog_context(db: AsyncSession, business: Business) -> AgentCatalogContext:
    product_result = await db.execute(
        select(Product, CatalogItem)
        .join(CatalogItem, CatalogItem.product_id == Product.id, isouter=True)
        .where(
            Product.business_id == business.id,
            Product.is_available == True,  # noqa: E712
        )
        .order_by(Product.category, Product.full_name)
    )
    products: list[AgentCatalogProductContext] = []
    summary: list[str] = []
    for product, catalog_item in product_result.all():
        product_context = AgentCatalogProductContext(
            product_id=product.id,
            code=product.code,
            short_name=product.short_name,
            full_name=product.full_name,
            description=product.description,
            category=product.category,
            price_large=_to_float(catalog_item.price_large) if catalog_item else None,
            price_small=_to_float(catalog_item.price_small) if catalog_item else None,
            price_unit=_to_float(catalog_item.price_unit) if catalog_item else None,
            price_dozen=_to_float(catalog_item.price_dozen) if catalog_item else None,
        )
        products.append(product_context)

        price_parts = [
            f"grande ${product_context.price_large:.2f}" if product_context.price_large is not None else None,
            f"chica ${product_context.price_small:.2f}" if product_context.price_small is not None else None,
            f"unidad ${product_context.price_unit:.2f}" if product_context.price_unit is not None else None,
            f"docena ${product_context.price_dozen:.2f}" if product_context.price_dozen is not None else None,
        ]
        visible_prices = ", ".join(part for part in price_parts if part)
        if visible_prices:
            summary.append(f"{product.full_name}: {visible_prices}")
        else:
            summary.append(product.full_name)

    combo_result = await db.execute(
        select(Combo)
        .options(selectinload(Combo.items).selectinload(ComboItem.product))
        .where(
            Combo.business_id == business.id,
            Combo.is_available == True,  # noqa: E712
        )
        .order_by(Combo.full_name)
    )
    combos: list[AgentCatalogComboContext] = []
    for combo in combo_result.scalars().all():
        item_parts: list[str] = []
        for combo_item in combo.items:
            if combo_item.is_open:
                item_parts.append(f"{combo_item.quantity}x {combo_item.open_category} a elecci\u00f3n")
            elif combo_item.product:
                item_parts.append(f"{combo_item.quantity}x {combo_item.product.short_name}")
        items_description = ", ".join(item_parts)
        combos.append(
            AgentCatalogComboContext(
                combo_id=combo.id,
                code=combo.code,
                short_name=combo.short_name,
                full_name=combo.full_name,
                description=combo.description,
                price=float(combo.price),
                items_description=items_description,
            )
        )
        summary.append(f"{combo.full_name}: ${float(combo.price):.2f} ({items_description})")

    return AgentCatalogContext(products=products, combos=combos, summary=summary)


def _build_rules_context(business: Business) -> AgentBusinessRulesContext:
    surcharge = float(getattr(business, "half_half_surcharge", 0) or 0)
    rules = [
        "No inventar productos, combos ni precios fuera del cat\u00e1logo disponible.",
        "No confirmar el pedido si faltan datos de entrega, total o medio de pago.",
        "Antes de cerrar la venta, resumir qu\u00e9 compra el cliente y el total final.",
        "Si el pedido es delivery, exigir calle, n\u00famero y entre calles antes de avanzar.",
        "Si hay mitad y mitad, aplicar solo el recargo configurado por el comercio.",
    ]
    return AgentBusinessRulesContext(half_half_surcharge=surcharge, rules=rules)


def _build_assistant_context(business: Business, rules: AgentBusinessRulesContext) -> AgentAssistantContext:
    assistant_name = business.assistant_name or f"Asistente de {business.name}"
    prompt_parts = [part.strip() for part in (
        business.assistant_system_prompt_master,
        business.assistant_system_prompt_default,
    ) if part and part.strip()]
    rules_block = "\n".join(f"- {rule}" for rule in rules.rules)
    prompt_parts.append(
        "\n".join(
            [
                f"Nombre del asistente: {assistant_name}",
                f"Comercio: {business.name}",
                f"Recargo mitad y mitad: ${rules.half_half_surcharge:.2f}",
                "Reglas operativas:",
                rules_block,
            ]
        )
    )
    effective_prompt = "\n\n".join(prompt_parts)
    return AgentAssistantContext(
        name=assistant_name,
        system_prompt_master=business.assistant_system_prompt_master,
        system_prompt_default=business.assistant_system_prompt_default,
        effective_system_prompt=effective_prompt,
    )


def _build_session_state(session: ConversationSession, active_order: Order | None) -> AgentSessionState:
    raw_state = session.agent_state or {}
    state = AgentSessionState.model_validate(raw_state) if raw_state else AgentSessionState()
    if active_order is not None:
        state.active_order_id = active_order.id
        if state.draft_order_id is None and active_order.status == "in_progress":
            state.draft_order_id = active_order.id
    return state


async def build_agent_context(
    db: AsyncSession,
    business_id: uuid.UUID,
    phone: str,
    recent_messages_limit: int = 20,
) -> AgentResolvedContext:
    business = await _get_business_or_404(db, business_id)
    normalized_phone = _normalize_phone(phone)

    customer = await _get_or_create_customer(db, business_id, normalized_phone)
    session = await _get_or_create_session(db, business_id, customer.id)
    active_order = await _get_active_order(db, business_id, customer.id)

    message_result = await db.execute(
        select(Message)
        .where(Message.session_id == session.id)
        .order_by(Message.sent_at.desc())
        .limit(recent_messages_limit)
    )
    recent_messages = [
        AgentMessageContext(
            direction=message.direction,
            content=message.content,
            sent_at=message.sent_at,
            sender_phone=message.sender_phone,
            sender_name=message.sender_name,
        )
        for message in reversed(message_result.scalars().all())
    ]

    rules = _build_rules_context(business)
    catalog = await _build_catalog_context(db, business)
    assistant = _build_assistant_context(business, rules)
    order_context = await _build_order_context(db, active_order)
    session_state = _build_session_state(session, active_order)

    await db.commit()

    return AgentResolvedContext(
        business_id=business.id,
        business_name=business.name,
        session_id=session.id,
        session_status=session.status,
        agent_state=session_state,
        assistant=assistant,
        customer=AgentCustomerContext(
            customer_id=customer.id,
            phone=None if _looks_like_lid(customer.phone) else customer.phone,
            whatsapp_lid=_extract_whatsapp_lid(customer),
            whatsapp_wa_id=customer.whatsapp_wa_id,
            name=customer.name,
            whatsapp_display_name=customer.whatsapp_display_name,
            whatsapp_profile_name=customer.whatsapp_profile_name,
            whatsapp_business_name=customer.whatsapp_business_name,
            address=customer.address,
            credit_balance=float(customer.credit_balance),
            has_whatsapp=customer.has_whatsapp,
        ),
        active_order=order_context,
        recent_messages=recent_messages,
        catalog=catalog,
        rules=rules,
    )
