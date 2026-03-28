from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import (
    ActivePizzeriaId,
    DBSession,
    OwnerOrAdminRequired,
    TokenPayloadDep,
)
from app.models.catalog import CatalogItem, Combo, Product
from app.models.customer import Customer
from app.models.order import Incident, Order, OrderItem, OrderStatus, Payment, PaymentStatus
from app.schemas.order import (
    IncidentCreate,
    IncidentRead,
    OrderCreate,
    OrderRead,
    OrderStatusUpdate,
    PaymentCreate,
    PaymentRead,
)

router = APIRouter(tags=["pedidos"])

# ---------------------------------------------------------------------------
# Máquina de estados
# ---------------------------------------------------------------------------

# Transiciones válidas en el flujo normal
_VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.in_progress: {
        OrderStatus.pending_payment,
        OrderStatus.pending_preparation,
        OrderStatus.cancelled,
        OrderStatus.discarded,
    },
    OrderStatus.pending_payment: {
        OrderStatus.pending_preparation,
        OrderStatus.cancelled,
        OrderStatus.discarded,
    },
    OrderStatus.pending_preparation: {
        OrderStatus.in_preparation,
        OrderStatus.cancelled,
        OrderStatus.with_incident,
        OrderStatus.discarded,
    },
    OrderStatus.in_preparation: {
        OrderStatus.ready_for_dispatch,
        OrderStatus.with_incident,
        OrderStatus.discarded,
    },
    OrderStatus.ready_for_dispatch: {
        OrderStatus.in_delivery,
        OrderStatus.with_incident,
        OrderStatus.discarded,
    },
    OrderStatus.in_delivery: {
        OrderStatus.delivered,
        OrderStatus.with_incident,
        OrderStatus.discarded,
    },
    OrderStatus.with_incident: {
        OrderStatus.pending_preparation,
        OrderStatus.in_preparation,
        OrderStatus.cancelled,
        OrderStatus.discarded,
    },
    # Estados terminales — sin transiciones
    OrderStatus.delivered: set(),
    OrderStatus.cancelled: set(),
    OrderStatus.discarded: set(),
}

# Roles que pueden cancelar un pedido
_CANCEL_ROLES = {"owner", "admin", "cajero"}


def _validate_transition(current: OrderStatus, target: OrderStatus) -> None:
    """Lanza 422 si la transición de estado no es válida."""
    allowed = _VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Transición inválida: '{current.value}' → '{target.value}'. "
                f"Transiciones permitidas: {[s.value for s in allowed] or 'ninguna (estado terminal)'}."
            ),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_order(order_id: int, pizzeria_id: int, db: DBSession) -> Order:
    """Devuelve el pedido con sus ítems cargados. Lanza 404 si no pertenece a la pizzería."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(
            Order.id == order_id,
            Order.pizzeria_id == pizzeria_id,
            Order.deleted_at.is_(None),
        )
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
    return order


def _compute_total(items: list[OrderItem]) -> float:
    return sum(float(i.unit_price) * i.quantity for i in items)


# ---------------------------------------------------------------------------
# Pedidos — CRUD
# ---------------------------------------------------------------------------

@router.post(
    "/pizzerias/{pizzeria_id}/pedidos",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
    pizzeria_id: int,
    body: OrderCreate,
    active_pid: ActivePizzeriaId,
    db: DBSession,
) -> OrderRead:
    """
    Crea un pedido en estado 'in_progress'. Valida que el cliente y todos los
    productos/combos pertenezcan a la pizzería activa.
    """
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    # Validar cliente
    customer = await db.execute(
        select(Customer).where(
            Customer.id == body.customer_id,
            Customer.pizzeria_id == active_pid,
        )
    )
    if customer.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado en esta pizzería",
        )

    if not body.items:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El pedido debe tener al menos un ítem",
        )

    # Validar que cada ítem tiene exactamente product_id o combo_id
    for idx, item in enumerate(body.items):
        if bool(item.product_id) == bool(item.combo_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Ítem {idx}: debe tener product_id o combo_id, no ambos ni ninguno",
            )
        if item.product_id:
            prod = await db.execute(
                select(Product).where(
                    Product.id == item.product_id,
                    Product.pizzeria_id == active_pid,
                    Product.deleted_at.is_(None),
                    Product.is_available.is_(True),
                )
            )
            if prod.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Producto {item.product_id} no disponible en esta pizzería",
                )
        if item.combo_id:
            combo = await db.execute(
                select(Combo).where(
                    Combo.id == item.combo_id,
                    Combo.pizzeria_id == active_pid,
                    Combo.deleted_at.is_(None),
                    Combo.is_available.is_(True),
                )
            )
            if combo.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Combo {item.combo_id} no disponible en esta pizzería",
                )

    order = Order(
        pizzeria_id=active_pid,
        customer_id=body.customer_id,
        whatsapp_number_id=body.whatsapp_number_id,
        origin=body.origin,
        notes=body.notes,
        status=OrderStatus.in_progress,
        total=0,
    )
    db.add(order)
    await db.flush()

    order_items: list[OrderItem] = []
    for item_data in body.items:
        oi = OrderItem(
            order_id=order.id,
            product_id=item_data.product_id,
            combo_id=item_data.combo_id,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            notes=item_data.notes,
        )
        db.add(oi)
        order_items.append(oi)

    await db.flush()
    order.total = _compute_total(order_items)
    await db.commit()

    # Recargar con ítems
    return OrderRead.model_validate(await _get_order(order.id, active_pid, db))


@router.get("/pizzerias/{pizzeria_id}/pedidos", response_model=list[OrderRead])
async def list_orders(
    pizzeria_id: int,
    active_pid: ActivePizzeriaId,
    db: DBSession,
    order_status: OrderStatus | None = Query(default=None, alias="status"),
    customer_id: int | None = None,
) -> list[OrderRead]:
    """Lista pedidos de la pizzería. Filtra opcionalmente por estado o cliente."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.pizzeria_id == active_pid, Order.deleted_at.is_(None))
    )
    if order_status is not None:
        stmt = stmt.where(Order.status == order_status)
    if customer_id is not None:
        stmt = stmt.where(Order.customer_id == customer_id)

    result = await db.execute(stmt.order_by(Order.created_at.desc()))
    return [OrderRead.model_validate(o) for o in result.scalars()]


@router.get("/pizzerias/{pizzeria_id}/pedidos/{order_id}", response_model=OrderRead)
async def get_order(
    pizzeria_id: int,
    order_id: int,
    active_pid: ActivePizzeriaId,
    db: DBSession,
) -> OrderRead:
    """Detalle de un pedido con sus ítems."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    order = await _get_order(order_id, active_pid, db)
    return OrderRead.model_validate(order)


# ---------------------------------------------------------------------------
# Transiciones de estado
# ---------------------------------------------------------------------------

@router.patch(
    "/pizzerias/{pizzeria_id}/pedidos/{order_id}/estado",
    response_model=OrderRead,
)
async def update_order_status(
    pizzeria_id: int,
    order_id: int,
    body: OrderStatusUpdate,
    active_pid: ActivePizzeriaId,
    payload: TokenPayloadDep,
    db: DBSession,
) -> OrderRead:
    """
    Cambia el estado de un pedido siguiendo la máquina de estados definida.
    Solo roles autorizados pueden cancelar.
    """
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    order = await _get_order(order_id, active_pid, db)

    if body.status == OrderStatus.cancelled and payload.role not in _CANCEL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo owner, admin o cajero pueden cancelar pedidos",
        )

    _validate_transition(order.status, body.status)

    order.status = body.status
    await db.commit()
    await db.refresh(order)
    return OrderRead.model_validate(await _get_order(order_id, active_pid, db))


# ---------------------------------------------------------------------------
# Pagos
# ---------------------------------------------------------------------------

@router.post(
    "/pizzerias/{pizzeria_id}/pedidos/{order_id}/pagos",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_payment(
    pizzeria_id: int,
    order_id: int,
    body: PaymentCreate,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> PaymentRead:
    """Registra un pago para el pedido."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    order = await _get_order(order_id, active_pid, db)

    if order.status in (OrderStatus.cancelled, OrderStatus.discarded):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se puede registrar un pago en un pedido cancelado o descartado",
        )

    payment = Payment(
        order_id=order_id,
        pizzeria_id=active_pid,
        method=body.method,
        amount=body.amount,
        external_reference=body.external_reference,
        status=PaymentStatus.pending,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return PaymentRead.model_validate(payment)


@router.get(
    "/pizzerias/{pizzeria_id}/pedidos/{order_id}/pagos",
    response_model=list[PaymentRead],
)
async def list_payments(
    pizzeria_id: int,
    order_id: int,
    active_pid: ActivePizzeriaId,
    db: DBSession,
) -> list[PaymentRead]:
    """Lista los pagos de un pedido."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    await _get_order(order_id, active_pid, db)

    result = await db.execute(
        select(Payment).where(
            Payment.order_id == order_id,
            Payment.pizzeria_id == active_pid,
        ).order_by(Payment.created_at)
    )
    return [PaymentRead.model_validate(p) for p in result.scalars()]


@router.patch(
    "/pizzerias/{pizzeria_id}/pedidos/{order_id}/pagos/{payment_id}",
    response_model=PaymentRead,
)
async def update_payment_status(
    pizzeria_id: int,
    order_id: int,
    payment_id: int,
    payment_status: PaymentStatus,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> PaymentRead:
    """Actualiza el estado de un pago (confirmado, rechazado, reembolsado)."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    await _get_order(order_id, active_pid, db)

    result = await db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.order_id == order_id,
            Payment.pizzeria_id == active_pid,
        )
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado")

    payment.status = payment_status
    await db.commit()
    await db.refresh(payment)
    return PaymentRead.model_validate(payment)


# ---------------------------------------------------------------------------
# Incidencias
# ---------------------------------------------------------------------------

@router.post(
    "/pizzerias/{pizzeria_id}/pedidos/{order_id}/incidencias",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_incident(
    pizzeria_id: int,
    order_id: int,
    body: IncidentCreate,
    active_pid: ActivePizzeriaId,
    db: DBSession,
) -> IncidentRead:
    """Registra una incidencia en el pedido y lo mueve a estado 'with_incident'."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    order = await _get_order(order_id, active_pid, db)

    _validate_transition(order.status, OrderStatus.with_incident)

    incident = Incident(
        order_id=order_id,
        pizzeria_id=active_pid,
        type=body.type,
        description=body.description,
    )
    db.add(incident)

    order.status = OrderStatus.with_incident
    await db.commit()
    await db.refresh(incident)
    return IncidentRead.model_validate(incident)


@router.patch(
    "/pizzerias/{pizzeria_id}/pedidos/{order_id}/incidencias/{incident_id}",
    response_model=IncidentRead,
)
async def resolve_incident(
    pizzeria_id: int,
    order_id: int,
    incident_id: int,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> IncidentRead:
    """Marca una incidencia como resuelta."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    await _get_order(order_id, active_pid, db)

    result = await db.execute(
        select(Incident).where(
            Incident.id == incident_id,
            Incident.order_id == order_id,
            Incident.pizzeria_id == active_pid,
        )
    )
    incident = result.scalar_one_or_none()
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incidencia no encontrada"
        )

    incident.is_resolved = True
    await db.commit()
    await db.refresh(incident)
    return IncidentRead.model_validate(incident)
