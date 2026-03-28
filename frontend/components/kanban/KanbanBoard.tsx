"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { Order, OrderStatus } from "@/lib/types";
import KanbanColumn from "./KanbanColumn";

const POLL_INTERVAL_MS = 15_000;

interface ColumnDef {
  status: OrderStatus;
  label: string;
  nextStatus: OrderStatus | null;
  nextLabel: string | null;
  color: string;
}

const COLUMNS: ColumnDef[] = [
  {
    status: "in_progress",
    label: "Nuevo",
    nextStatus: "pending_payment",
    nextLabel: "Cobrar",
    color: "bg-blue-100 text-blue-800",
  },
  {
    status: "pending_payment",
    label: "Pendiente pago",
    nextStatus: "pending_preparation",
    nextLabel: "Pago OK",
    color: "bg-yellow-100 text-yellow-800",
  },
  {
    status: "pending_preparation",
    label: "Para preparar",
    nextStatus: "in_preparation",
    nextLabel: "Preparar",
    color: "bg-orange-100 text-orange-800",
  },
  {
    status: "in_preparation",
    label: "En preparación",
    nextStatus: "ready_for_dispatch",
    nextLabel: "Listo",
    color: "bg-purple-100 text-purple-800",
  },
  {
    status: "ready_for_dispatch",
    label: "Para despachar",
    nextStatus: "in_delivery",
    nextLabel: "Despachar",
    color: "bg-indigo-100 text-indigo-800",
  },
  {
    status: "in_delivery",
    label: "En delivery",
    nextStatus: "delivered",
    nextLabel: "Entregado",
    color: "bg-teal-100 text-teal-800",
  },
  {
    status: "with_incident",
    label: "⚠ Incidencia",
    nextStatus: null,
    nextLabel: null,
    color: "bg-red-100 text-red-800",
  },
];

export default function KanbanBoard({ pizzeriaId }: { pizzeriaId: string }) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [advancingId, setAdvancingId] = useState<number | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchOrders = useCallback(async () => {
    try {
      const active = COLUMNS.map((c) => c.status)
        .filter((s) => s !== "delivered" && s !== "cancelled" && s !== "discarded");

      // Fetch todas las columnas activas en paralelo
      const results = await Promise.all(
        active.map((s) =>
          apiFetch<Order[]>(
            `/pizzerias/${pizzeriaId}/pedidos?status=${s}`
          )
        )
      );
      setOrders(results.flat());
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Sesión expirada. Recargá la página.");
      } else {
        setError("Error al cargar pedidos");
      }
    } finally {
      setLoading(false);
    }
  }, [pizzeriaId]);

  useEffect(() => {
    fetchOrders();
    timerRef.current = setInterval(fetchOrders, POLL_INTERVAL_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [fetchOrders]);

  async function handleAdvance(orderId: number, targetStatus: string) {
    setAdvancingId(orderId);
    try {
      await apiFetch(`/pizzerias/${pizzeriaId}/pedidos/${orderId}/estado`, {
        method: "PATCH",
        body: JSON.stringify({ status: targetStatus }),
      });
      await fetchOrders();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al actualizar pedido");
    } finally {
      setAdvancingId(null);
    }
  }

  async function handleCancel(orderId: number) {
    if (!confirm(`¿Cancelar pedido #${orderId}?`)) return;
    setAdvancingId(orderId);
    try {
      await apiFetch(`/pizzerias/${pizzeriaId}/pedidos/${orderId}/estado`, {
        method: "PATCH",
        body: JSON.stringify({ status: "cancelled" }),
      });
      await fetchOrders();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cancelar pedido");
    } finally {
      setAdvancingId(null);
    }
  }

  const ordersByStatus = (status: OrderStatus) =>
    orders.filter((o) => o.status === status);

  return (
    <div className="flex flex-col h-full">
      {/* Barra superior del tablero */}
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-border">
        <h2 className="font-semibold text-foreground">Tablero de pedidos</h2>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-xs text-muted-foreground">
              Actualizado {lastUpdated.toLocaleTimeString("es-AR", { timeStyle: "short" })}
            </span>
          )}
          <button
            onClick={() => fetchOrders()}
            className="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-secondary transition-colors"
          >
            ↺ Actualizar
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mt-3 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Tablero */}
      {loading ? (
        <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
          Cargando pedidos…
        </div>
      ) : (
        <div className="flex-1 overflow-x-auto px-4 py-4">
          <div className="flex gap-3 h-full">
            {COLUMNS.map((col) => (
              <KanbanColumn
                key={col.status}
                column={col}
                orders={ordersByStatus(col.status)}
                onAdvance={handleAdvance}
                onCancel={handleCancel}
                advancingId={advancingId}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
