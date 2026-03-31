"""Lógica de negocio para pedidos."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import User, UserBusiness
from app.models.customer import Customer
from app.models.order import Incident, Order, OrderItem, OrderStatusHistory
from app.services.notificaciones import notificar_cambio_estado, notificar_cancelacion
from app.schemas.pedidos import (
    IncidentCreate,
    OrderAssignDelivery,
    OrderCancel,
    OrderCreate,
    OrderItemResponse,
    OrderListItem,
    OrderResponse,
    OrderUpdateNotes,
    OrderUpdatePayment,
    OrderUpdateStatus,
    StatusHistoryResponse,
    IncidentResponse,
    CustomerSummary,
)

# Transiciones de estado válidas según rol
# Mapa: estado_actual -> {rol: [estados_destino_permitidos]}
VALID_TRANSITIONS: dict[str, dict[str, list[str]]] = {
    "pending_preparation": {
        "cook":    ["in_preparation"],
        "cashier": ["in_preparation", "cancelled"],
        "admin":   ["in_preparation", "cancelled"],
        "owner":   ["in_preparation", "cancelled"],
    },
    "in_preparation": {
        "cook":    ["to_dispatch"],
        "cashier": ["to_dispatch", "cancelled"],
        "admin":   ["to_dispatch", "cancelled"],
        "owner":   ["to_dispatch", "cancelled"],
    },
    "to_dispatch": {
        "delivery": ["in_delivery"],
        "cashier":  ["in_delivery", "cancelled"],
        "admin":    ["in_delivery", "cancelled"],
        "owner":    ["in_delivery", "cancelled"],
    },
    "in_delivery": {
        "delivery": ["delivered", "with_incident"],
        "cashier":  ["delivered", "with_incident", "cancelled"],
        "admin":    ["delivered", "with_incident", "cancelled"],
        "owner":    ["delivered", "with_incident", "cancelled"],
    },
    "with_incident": {
        "cashier": ["in_delivery", "cancelled"],
        "admin":   ["in_delivery", "cancelled"],
        "owner":   ["in_delivery", "cancelled"],
    },
}

# Roles que pueden cancelar
ROLES_CANCELACION = {"cashier", "admin", "owner"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _siguiente_order_number(db: AsyncSession, business_id: uuid.UUID) -> int:
    """Obtiene el próximo número de pedido para el comercio."""
    result = await db.execute(
        select(func.max(Order.order_number)).where(Order.business_id == business_id)
    )
    max_num = result.scalar_one_or_none()
    return (max_num or 0) + 1


async def _registrar_historial(
    db: AsyncSession,
    order: Order,
    new_status: str,
    changed_by_id: uuid.UUID | None = None,
    note: str | None = None,
) -> None:
    """Registra un cambio de estado en el historial."""
    entry = OrderStatusHistory(
        order_id=order.id,
        previous_status=order.status,
        new_status=new_status,
        changed_by=changed_by_id,
        note=note,
    )
    db.add(entry)


async def _build_order_response(db: AsyncSession, order: Order) -> OrderResponse:
    """Construye el schema de respuesta completo de un pedido."""
    # Cargar nombres del historial
    history_responses: list[StatusHistoryResponse] = []
    for h in order.status_history:
        changed_by_name = None
        if h.changed_by:
            res = await db.execute(select(User.name).where(User.id == h.changed_by))
            changed_by_name = res.scalar_one_or_none()
        history_responses.append(
            StatusHistoryResponse(
                id=h.id,
                previous_status=h.previous_status,
                new_status=h.new_status,
                changed_by=h.changed_by,
                changed_by_name=changed_by_name,
                changed_at=h.changed_at,
                note=h.note,
            )
        )

    # Cargar nombres de incidencias
    incident_responses: list[IncidentResponse] = []
    for inc in order.incidents:
        reported_by_name = None
        if inc.reported_by:
            res = await db.execute(select(User.name).where(User.id == inc.reported_by))
            reported_by_name = res.scalar_one_or_none()
        incident_responses.append(
            IncidentResponse(
                id=inc.id,
                type=inc.type,
                description=inc.description,
                reported_by=inc.reported_by,
                reported_by_name=reported_by_name,
                status=inc.status,
                resolved_at=inc.resolved_at,
                created_at=inc.created_at,
            )
        )

    # Items con nombre descriptivo
    item_responses: list[OrderItemResponse] = []
    for item in order.items:
        display_name = None
        if item.product_id:
            from app.models.catalog import Product  # import local para evitar ciclo
            res = await db.execute(
                select(Product.full_name).where(Product.id == item.product_id)
            )
            display_name = res.scalar_one_or_none()
        elif item.combo_id:
            from app.models.catalog import Combo
            res = await db.execute(
                select(Combo.full_name).where(Combo.id == item.combo_id)
            )
            display_name = res.scalar_one_or_none()
        item_responses.append(
            OrderItemResponse(
                id=item.id,
                product_id=item.product_id,
                combo_id=item.combo_id,
                quantity=item.quantity,
                unit_price=float(item.unit_price),
                variant=item.variant,
                notes=item.notes,
                display_name=display_name,
            )
        )

    return OrderResponse(
        id=order.id,
        business_id=order.business_id,
        order_number=order.order_number,
        customer=CustomerSummary(
            id=order.customer.id,
            name=order.customer.name,
            phone=order.customer.phone,
        ),
        status=order.status,
        payment_status=order.payment_status,
        origin=order.origin,
        delivery_type=order.delivery_type,
        delivery_address=order.delivery_address,
        total_amount=float(order.total_amount),
        credit_applied=float(order.credit_applied),
        delivery_person_id=order.delivery_person_id,
        internal_notes=order.internal_notes,
        kitchen_notes=order.kitchen_notes,
        delivery_notes=order.delivery_notes,
        created_by=order.created_by,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=item_responses,
        status_history=history_responses,
        incidents=incident_responses,
    )


async def listar_pedidos(
    db: AsyncSession,
    business_id: uuid.UUID,
    status_filter: str | None,
    payment_status_filter: str | None,
    delivery_person_filter: uuid.UUID | None,
    page: int,
    page_size: int,
    user_role: str,
    user_id: uuid.UUID,
) -> tuple[list[OrderListItem], int]:
    """Lista pedidos con filtros. Aplica restricciones de visibilidad por rol."""
    query = (
        select(Order)
        .where(Order.business_id == business_id)
        .options(
            selectinload(Order.customer),
            selectinload(Order.items),
        )
    )

    # Restricciones de visibilidad por rol
    if user_role == "cook":
        query = query.where(Order.status.in_(["pending_preparation", "in_preparation"]))
    elif user_role == "delivery":
        query = query.where(
            Order.status.in_(["to_dispatch", "in_delivery", "with_incident"]),
        )

    # Filtros opcionales
    if status_filter:
        query = query.where(Order.status == status_filter)
    if payment_status_filter:
        query = query.where(Order.payment_status == payment_status_filter)
    if delivery_person_filter:
        query = query.where(Order.delivery_person_id == delivery_person_filter)

    # Total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Paginación — más antiguos primero
    query = query.order_by(Order.created_at.asc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    orders = result.scalars().all()

    items: list[OrderListItem] = []
    for order in orders:
        items_summary: list[str] = []
        for item in order.items:
            if item.product_id:
                from app.models.catalog import Product
                res = await db.execute(select(Product.short_name).where(Product.id == item.product_id))
                name = res.scalar_one_or_none() or "Producto"
            elif item.combo_id:
                from app.models.catalog import Combo
                res = await db.execute(select(Combo.short_name).where(Combo.id == item.combo_id))
                name = res.scalar_one_or_none() or "Combo"
            else:
                name = "Ítem"
            items_summary.append(f"{item.quantity}x {name}")

        items.append(
            OrderListItem(
                id=order.id,
                order_number=order.order_number,
                customer=CustomerSummary(
                    id=order.customer.id,
                    name=order.customer.name,
                    phone=order.customer.phone,
                ),
                status=order.status,
                payment_status=order.payment_status,
                origin=order.origin,
                delivery_type=order.delivery_type,
                total_amount=float(order.total_amount),
                delivery_person_id=order.delivery_person_id,
                created_at=order.created_at,
                items_summary=items_summary,
            )
        )

    return items, total


async def obtener_pedido(
    db: AsyncSession,
    business_id: uuid.UUID,
    order_id: uuid.UUID,
) -> OrderResponse:
    """Obtiene el detalle completo de un pedido."""
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.business_id == business_id)
        .options(
            selectinload(Order.customer),
            selectinload(Order.items),
            selectinload(Order.status_history),
            selectinload(Order.incidents),
        )
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")

    return await _build_order_response(db, order)


async def crear_pedido(
    db: AsyncSession,
    business_id: uuid.UUID,
    data: OrderCreate,
    created_by_id: uuid.UUID,
) -> OrderResponse:
    """Crea un pedido manual (operador/cajero)."""
    # Verificar cliente existe y pertenece al comercio
    cust_result = await db.execute(
        select(Customer).where(
            Customer.id == data.customer_id,
            Customer.business_id == business_id,
        )
    )
    customer = cust_result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")

    order_number = await _siguiente_order_number(db, business_id)

    # Los pedidos telefónicos entran directo a preparación (ya son aceptados al crearse)
    initial_status = "in_preparation" if data.origin == "phone" else "pending_preparation"

    order = Order(
        business_id=business_id,
        order_number=order_number,
        customer_id=data.customer_id,
        status=initial_status,
        payment_status=data.payment_status,
        origin=data.origin,
        delivery_type=data.delivery_type,
        delivery_address=data.delivery_address,
        total_amount=data.total_amount,
        credit_applied=data.credit_applied,
        kitchen_notes=data.kitchen_notes,
        delivery_notes=data.delivery_notes,
        created_by=created_by_id,
    )
    db.add(order)
    await db.flush()

    # Items
    for item_data in data.items:
        item = OrderItem(
            order_id=order.id,
            product_id=item_data.product_id,
            combo_id=item_data.combo_id,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            variant=item_data.variant,
            notes=item_data.notes,
        )
        db.add(item)

    # Primer entrada en el historial
    hist_note = "Pedido telefónico — en preparación" if data.origin == "phone" else "Pedido creado por operador"
    await _registrar_historial(
        db, order, initial_status, changed_by_id=created_by_id,
        note=hist_note
    )

    await db.commit()

    # Recargar con relaciones
    return await obtener_pedido(db, business_id, order.id)


async def cambiar_estado(
    db: AsyncSession,
    business_id: uuid.UUID,
    order_id: uuid.UUID,
    data: OrderUpdateStatus,
    user_id: uuid.UUID,
    user_role: str,
) -> OrderResponse:
    """Cambia el estado de un pedido validando la transición y el rol."""
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.business_id == business_id)
        .options(selectinload(Order.customer), selectinload(Order.items),
                 selectinload(Order.status_history), selectinload(Order.incidents))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")

    allowed = VALID_TRANSITIONS.get(order.status, {}).get(user_role, [])
    if data.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transición no permitida: {order.status} → {data.status} para rol {user_role}",
        )

    await _registrar_historial(db, order, data.status, changed_by_id=user_id, note=data.note)
    prev_phone = order.customer.phone
    prev_delivery_type = order.delivery_type
    prev_total = float(order.total_amount)
    prev_number = order.order_number
    order.status = data.status
    await db.commit()
    await db.refresh(order)

    # Notificación automática al cliente (fire-and-forget)
    await notificar_cambio_estado(
        business_id=business_id,
        order_number=prev_number,
        new_status=data.status,
        delivery_type=prev_delivery_type,
        customer_phone=prev_phone,
        total_amount=prev_total,
        db=db,
    )

    return await obtener_pedido(db, business_id, order.id)


async def marcar_pagado(
    db: AsyncSession,
    business_id: uuid.UUID,
    order_id: uuid.UUID,
    data: OrderUpdatePayment,
    user_role: str,
) -> OrderResponse:
    """Actualiza el estado de pago de un pedido."""
    if user_role not in {"cashier", "admin", "owner"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permiso para marcar pago")

    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.business_id == business_id)
        .options(selectinload(Order.customer), selectinload(Order.items),
                 selectinload(Order.status_history), selectinload(Order.incidents))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")

    order.payment_status = data.payment_status
    await db.commit()
    await db.refresh(order)
    return await obtener_pedido(db, business_id, order.id)


async def asignar_repartidor(
    db: AsyncSession,
    business_id: uuid.UUID,
    order_id: uuid.UUID,
    data: OrderAssignDelivery,
    user_role: str,
) -> OrderResponse:
    """Asigna un repartidor a un pedido."""
    if user_role not in {"cashier", "admin", "owner"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permiso para asignar repartidor")

    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.business_id == business_id)
        .options(selectinload(Order.customer), selectinload(Order.items),
                 selectinload(Order.status_history), selectinload(Order.incidents))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")

    # Verificar que el repartidor pertenece al comercio
    if data.delivery_person_id:
        ub_result = await db.execute(
            select(UserBusiness).where(
                UserBusiness.user_id == data.delivery_person_id,
                UserBusiness.business_id == business_id,
                UserBusiness.is_active == True,  # noqa: E712
            )
        )
        if ub_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repartidor no encontrado en el comercio")

    order.delivery_person_id = data.delivery_person_id
    await db.commit()
    await db.refresh(order)
    return await obtener_pedido(db, business_id, order.id)


async def actualizar_notas(
    db: AsyncSession,
    business_id: uuid.UUID,
    order_id: uuid.UUID,
    data: OrderUpdateNotes,
) -> OrderResponse:
    """Actualiza las notas internas de un pedido."""
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.business_id == business_id)
        .options(selectinload(Order.customer), selectinload(Order.items),
                 selectinload(Order.status_history), selectinload(Order.incidents))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")

    order.internal_notes = data.internal_notes
    await db.commit()
    await db.refresh(order)
    return await obtener_pedido(db, business_id, order.id)


async def cancelar_pedido(
    db: AsyncSession,
    business_id: uuid.UUID,
    order_id: uuid.UUID,
    data: OrderCancel,
    user_id: uuid.UUID,
    user_role: str,
) -> OrderResponse:
    """Cancela un pedido aplicando la política de pago correspondiente."""
    if user_role not in ROLES_CANCELACION:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permiso para cancelar pedidos")

    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.business_id == business_id)
        .options(selectinload(Order.customer), selectinload(Order.items),
                 selectinload(Order.status_history), selectinload(Order.incidents))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")

    if order.status == "delivered":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede cancelar un pedido ya entregado",
        )

    # Determinar política de pago según el estado actual
    if data.payment_policy:
        payment_policy = data.payment_policy
    else:
        if order.status in ("in_progress", "pending_payment"):
            payment_policy = "no_charge"
        elif order.status in ("pending_preparation", "in_preparation"):
            # Si el pago fue confirmado → crédito; si no → sin cargo
            payment_policy = "credit" if order.payment_status == "paid" else "no_charge"
        else:
            payment_policy = "no_charge"

    # Si corresponde crédito, actualizar saldo del cliente
    if payment_policy == "credit":
        cust_result = await db.execute(
            select(Customer).where(Customer.id == order.customer_id)
        )
        customer = cust_result.scalar_one_or_none()
        if customer is not None:
            customer.credit_balance = float(customer.credit_balance) + float(order.total_amount)

    prev_phone = order.customer.phone
    prev_total = float(order.total_amount)
    prev_number = order.order_number

    await _registrar_historial(
        db, order, "cancelled", changed_by_id=user_id, note=data.note
    )
    order.status = "cancelled"
    order.payment_status = payment_policy
    await db.commit()
    await db.refresh(order)

    # Notificación automática al cliente
    await notificar_cancelacion(
        business_id=business_id,
        order_number=prev_number,
        payment_policy=payment_policy,
        total_amount=prev_total,
        customer_phone=prev_phone,
        db=db,
    )

    return await obtener_pedido(db, business_id, order.id)


async def reportar_incidencia(
    db: AsyncSession,
    business_id: uuid.UUID,
    order_id: uuid.UUID,
    data: IncidentCreate,
    user_id: uuid.UUID,
    user_role: str,
) -> OrderResponse:
    """Reporta una incidencia en el pedido."""
    allowed_roles = {"cashier", "admin", "owner", "delivery"}
    if user_role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permiso para reportar incidencias")

    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.business_id == business_id)
        .options(selectinload(Order.customer), selectinload(Order.items),
                 selectinload(Order.status_history), selectinload(Order.incidents))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")

    incident = Incident(
        order_id=order.id,
        business_id=business_id,
        type=data.type,
        description=data.description,
        reported_by=user_id,
    )
    db.add(incident)

    await _registrar_historial(db, order, "with_incident", changed_by_id=user_id,
                               note=f"Incidencia: {data.type}")
    order.status = "with_incident"
    await db.commit()
    await db.refresh(order)
    return await obtener_pedido(db, business_id, order.id)


async def resolver_redespacho(
    db: AsyncSession,
    business_id: uuid.UUID,
    order_id: uuid.UUID,
    incident_id: uuid.UUID,
    user_id: uuid.UUID,
    user_role: str,
) -> OrderResponse:
    """Resuelve una incidencia con re-despacho."""
    if user_role not in {"cashier", "admin", "owner"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permiso para resolver incidencias")

    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.business_id == business_id)
        .options(selectinload(Order.customer), selectinload(Order.items),
                 selectinload(Order.status_history), selectinload(Order.incidents))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")

    # Marcar incidencia como resuelta
    inc_result = await db.execute(
        select(Incident).where(Incident.id == incident_id, Incident.order_id == order.id)
    )
    incident = inc_result.scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidencia no encontrada")

    incident.status = "resolved_redispatch"
    incident.resolved_at = _now()

    await _registrar_historial(db, order, "in_delivery", changed_by_id=user_id, note="Re-despacho")
    order.status = "in_delivery"
    await db.commit()
    await db.refresh(order)
    return await obtener_pedido(db, business_id, order.id)
