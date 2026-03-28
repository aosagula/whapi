from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.deps import ActivePizzeriaId, CurrentAccount, DBSession, OwnerRequired
from app.models.account import Pizzeria
from app.models.catalog import Combo, Product
from app.models.conversation import ChatSession, ChatSessionStatus
from app.models.order import Order, OrderItem, OrderStatus
from app.schemas.reportes import (
    ConsolidatedReport,
    DailyRevenue,
    OrdersSummary,
    PizzeriaReportSummary,
    TopProduct,
)

router = APIRouter(tags=["reportes"])


# ---------------------------------------------------------------------------
# Resumen de pedidos por pizzería
# ---------------------------------------------------------------------------

@router.get(
    "/pizzerias/{pizzeria_id}/reportes/resumen",
    response_model=OrdersSummary,
)
async def orders_summary(
    pizzeria_id: int,
    active_pid: ActivePizzeriaId,
    db: DBSession,
    days: int = Query(default=30, ge=1, le=365),
) -> OrdersSummary:
    """
    Totales de pedidos e ingresos en los últimos N días.
    Incluye desglose por estado y por origen.
    """
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    since = date.today() - timedelta(days=days)

    base = select(Order).where(
        Order.pizzeria_id == active_pid,
        Order.deleted_at.is_(None),
        func.date(Order.created_at) >= since,
    )

    result = await db.execute(base)
    orders = result.scalars().all()

    total_revenue = sum(float(o.total) for o in orders)
    by_status: dict[str, int] = {}
    by_origin: dict[str, int] = {}

    for o in orders:
        by_status[o.status.value] = by_status.get(o.status.value, 0) + 1
        by_origin[o.origin.value] = by_origin.get(o.origin.value, 0) + 1

    return OrdersSummary(
        total_orders=len(orders),
        total_revenue=round(total_revenue, 2),
        by_status=by_status,
        by_origin=by_origin,
    )


# ---------------------------------------------------------------------------
# Ingresos diarios
# ---------------------------------------------------------------------------

@router.get(
    "/pizzerias/{pizzeria_id}/reportes/ingresos-diarios",
    response_model=list[DailyRevenue],
)
async def daily_revenue(
    pizzeria_id: int,
    active_pid: ActivePizzeriaId,
    db: DBSession,
    days: int = Query(default=30, ge=1, le=365),
) -> list[DailyRevenue]:
    """Ingresos y cantidad de pedidos agrupados por día."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    since = date.today() - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(Order.created_at).label("day"),
            func.count(Order.id).label("cnt"),
            func.coalesce(func.sum(Order.total), 0).label("revenue"),
        )
        .where(
            Order.pizzeria_id == active_pid,
            Order.deleted_at.is_(None),
            Order.status.notin_([OrderStatus.cancelled, OrderStatus.discarded]),
            func.date(Order.created_at) >= since,
        )
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    )

    return [
        DailyRevenue(date=str(row.day), orders=row.cnt, revenue=round(float(row.revenue), 2))
        for row in result.all()
    ]


# ---------------------------------------------------------------------------
# Productos top
# ---------------------------------------------------------------------------

@router.get(
    "/pizzerias/{pizzeria_id}/reportes/productos-top",
    response_model=list[TopProduct],
)
async def top_products(
    pizzeria_id: int,
    active_pid: ActivePizzeriaId,
    db: DBSession,
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[TopProduct]:
    """Los N productos más vendidos por cantidad, excluyendo pedidos cancelados."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    since = date.today() - timedelta(days=days)

    # Productos individuales
    prod_result = await db.execute(
        select(
            Product.id,
            Product.full_name,
            func.sum(OrderItem.quantity).label("qty"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Product.pizzeria_id == active_pid,
            Order.pizzeria_id == active_pid,
            Order.deleted_at.is_(None),
            Order.status.notin_([OrderStatus.cancelled, OrderStatus.discarded]),
            func.date(Order.created_at) >= since,
        )
        .group_by(Product.id, Product.full_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
    )

    products = [
        TopProduct(
            id=row.id,
            name=row.full_name,
            category="product",
            quantity=int(row.qty),
            revenue=round(float(row.revenue), 2),
        )
        for row in prod_result.all()
    ]

    # Combos
    combo_result = await db.execute(
        select(
            Combo.id,
            Combo.name,
            func.sum(OrderItem.quantity).label("qty"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
        )
        .join(OrderItem, OrderItem.combo_id == Combo.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Combo.pizzeria_id == active_pid,
            Order.pizzeria_id == active_pid,
            Order.deleted_at.is_(None),
            Order.status.notin_([OrderStatus.cancelled, OrderStatus.discarded]),
            func.date(Order.created_at) >= since,
        )
        .group_by(Combo.id, Combo.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
    )

    combos = [
        TopProduct(
            id=row.id,
            name=row.name,
            category="combo",
            quantity=int(row.qty),
            revenue=round(float(row.revenue), 2),
        )
        for row in combo_result.all()
    ]

    # Unir y reordenar por cantidad
    merged = sorted(products + combos, key=lambda x: x.quantity, reverse=True)
    return merged[:limit]


# ---------------------------------------------------------------------------
# Reporte consolidado del dueño (cross-pizzería)
# ---------------------------------------------------------------------------

@router.get(
    "/reportes/consolidado",
    response_model=ConsolidatedReport,
)
async def consolidated_report(
    current_account: CurrentAccount,
    _: OwnerRequired,
    db: DBSession,
    days: int = Query(default=30, ge=1, le=365),
) -> ConsolidatedReport:
    """
    Vista consolidada de todas las pizzerías del dueño.
    Solo accesible con rol 'owner'.
    """
    since = date.today() - timedelta(days=days)

    pizzerias_result = await db.execute(
        select(Pizzeria).where(
            Pizzeria.account_id == current_account.id,
            Pizzeria.is_active.is_(True),
        )
    )
    pizzerias = pizzerias_result.scalars().all()

    summaries: list[PizzeriaReportSummary] = []
    total_revenue = 0.0
    total_orders = 0

    for piz in pizzerias:
        orders_result = await db.execute(
            select(func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
            .where(
                Order.pizzeria_id == piz.id,
                Order.deleted_at.is_(None),
                Order.status.notin_([OrderStatus.cancelled, OrderStatus.discarded]),
                func.date(Order.created_at) >= since,
            )
        )
        row = orders_result.one()
        cnt, rev = int(row[0]), float(row[1])

        sessions_result = await db.execute(
            select(func.count(ChatSession.id)).where(
                ChatSession.pizzeria_id == piz.id,
                ChatSession.status.notin_([ChatSessionStatus.closed]),
            )
        )
        active_sessions = int(sessions_result.scalar() or 0)

        summaries.append(
            PizzeriaReportSummary(
                pizzeria_id=piz.id,
                pizzeria_name=piz.name,
                total_orders=cnt,
                total_revenue=round(rev, 2),
                active_sessions=active_sessions,
            )
        )
        total_revenue += rev
        total_orders += cnt

    return ConsolidatedReport(
        total_revenue=round(total_revenue, 2),
        total_orders=total_orders,
        pizzerias=sorted(summaries, key=lambda s: s.total_revenue, reverse=True),
    )
