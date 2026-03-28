from __future__ import annotations

from pydantic import BaseModel


class OrdersSummary(BaseModel):
    """Resumen de pedidos de una pizzería en un período."""

    total_orders: int
    total_revenue: float
    by_status: dict[str, int]
    by_origin: dict[str, int]


class DailyRevenue(BaseModel):
    """Ingresos y pedidos agrupados por día."""

    date: str          # YYYY-MM-DD
    orders: int
    revenue: float


class TopProduct(BaseModel):
    """Producto o combo más vendido."""

    id: int
    name: str
    category: str      # "product" | "combo"
    quantity: int
    revenue: float


class PizzeriaReportSummary(BaseModel):
    """Resumen de una pizzería (vista consolidada del dueño)."""

    pizzeria_id: int
    pizzeria_name: str
    total_orders: int
    total_revenue: float
    active_sessions: int


class ConsolidatedReport(BaseModel):
    """Reporte consolidado de todas las pizzerías de la cuenta."""

    total_revenue: float
    total_orders: int
    pizzerias: list[PizzeriaReportSummary]
