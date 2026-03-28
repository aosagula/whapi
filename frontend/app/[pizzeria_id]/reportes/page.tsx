"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";

interface OrdersSummary {
  total_orders: number;
  total_revenue: number;
  by_status: Record<string, number>;
  by_origin: Record<string, number>;
}

interface DailyRevenue {
  date: string;
  orders: number;
  revenue: number;
}

interface TopProduct {
  id: number;
  name: string;
  category: string;
  quantity: number;
  revenue: number;
}

const STATUS_LABELS: Record<string, string> = {
  in_progress: "En curso",
  pending_payment: "Pend. pago",
  pending_preparation: "Pend. preparación",
  in_preparation: "En preparación",
  ready_for_dispatch: "A despacho",
  in_delivery: "En delivery",
  delivered: "Entregado",
  cancelled: "Cancelado",
  discarded: "Descartado",
  with_incident: "Con incidencia",
};

const ORIGIN_LABELS: Record<string, string> = {
  whatsapp: "WhatsApp",
  phone: "Telefónico",
  operator: "Operador",
};

export default function ReportesPage() {
  const params = useParams();
  const pizzeriaId = params.pizzeria_id as string;

  const [days, setDays] = useState(30);
  const [summary, setSummary] = useState<OrdersSummary | null>(null);
  const [daily, setDaily] = useState<DailyRevenue[]>([]);
  const [topProducts, setTopProducts] = useState<TopProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, d, t] = await Promise.all([
        apiFetch<OrdersSummary>(`/pizzerias/${pizzeriaId}/reportes/resumen?days=${days}`),
        apiFetch<DailyRevenue[]>(`/pizzerias/${pizzeriaId}/reportes/ingresos-diarios?days=${days}`),
        apiFetch<TopProduct[]>(`/pizzerias/${pizzeriaId}/reportes/productos-top?days=${days}&limit=10`),
      ]);
      setSummary(s);
      setDaily(d);
      setTopProducts(t);
    } catch {
      setError("Error al cargar reportes");
    } finally {
      setLoading(false);
    }
  }, [pizzeriaId, days]);

  useEffect(() => { load(); }, [load]);

  const maxRevenue = daily.length > 0 ? Math.max(...daily.map((d) => d.revenue)) : 1;
  const maxQty = topProducts.length > 0 ? Math.max(...topProducts.map((p) => p.quantity)) : 1;

  return (
    <div className="mx-auto max-w-screen-xl px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-foreground">Reportes</h1>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Período:</span>
          {[7, 14, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`rounded-md px-3 py-1 border transition-colors ${
                days === d
                  ? "bg-primary text-primary-foreground border-primary"
                  : "border-border hover:bg-secondary"
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-16 text-muted-foreground">Cargando...</div>
      ) : (
        <>
          {/* Summary cards */}
          {summary && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <SummaryCard label="Total pedidos" value={summary.total_orders.toString()} />
              <SummaryCard label="Ingresos totales" value={`$${summary.total_revenue.toLocaleString("es-AR", { minimumFractionDigits: 2 })}`} />
              <div className="rounded-xl border border-border bg-white p-4 shadow-sm col-span-1">
                <p className="text-xs text-muted-foreground mb-2 font-medium uppercase tracking-wide">Por estado</p>
                <div className="space-y-1">
                  {Object.entries(summary.by_status).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-sm">
                      <span className="text-muted-foreground">{STATUS_LABELS[k] ?? k}</span>
                      <span className="font-medium">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-xl border border-border bg-white p-4 shadow-sm col-span-1">
                <p className="text-xs text-muted-foreground mb-2 font-medium uppercase tracking-wide">Por origen</p>
                <div className="space-y-1">
                  {Object.entries(summary.by_origin).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-sm">
                      <span className="text-muted-foreground">{ORIGIN_LABELS[k] ?? k}</span>
                      <span className="font-medium">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Daily revenue bar chart */}
          <div className="rounded-xl border border-border bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-4">
              Ingresos diarios (últimos {days} días)
            </h2>
            {daily.length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">Sin datos en el período</p>
            ) : (
              <div className="overflow-x-auto">
                <div className="flex items-end gap-1 min-w-max h-40">
                  {daily.map((row) => {
                    const height = Math.max(4, (row.revenue / maxRevenue) * 140);
                    return (
                      <div key={row.date} className="flex flex-col items-center gap-1 group">
                        <div className="relative">
                          <div
                            className="w-8 rounded-t bg-primary/70 hover:bg-primary transition-colors cursor-default"
                            style={{ height: `${height}px` }}
                          />
                          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block z-10 bg-foreground text-background text-xs rounded px-2 py-1 whitespace-nowrap">
                            {row.date}<br />${row.revenue.toFixed(2)} · {row.orders} ped.
                          </div>
                        </div>
                        <span className="text-[9px] text-muted-foreground rotate-45 origin-left w-6 overflow-hidden whitespace-nowrap">
                          {row.date.slice(5)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Top products */}
          <div className="rounded-xl border border-border bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-4">
              Productos más vendidos
            </h2>
            {topProducts.length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">Sin datos en el período</p>
            ) : (
              <div className="space-y-2">
                {topProducts.map((p, i) => (
                  <div key={`${p.category}-${p.id}`} className="flex items-center gap-3">
                    <span className="w-5 text-xs text-muted-foreground text-right">{i + 1}</span>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-sm font-medium">{p.name}</span>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          <span
                            className={`rounded-full px-2 py-0.5 ${
                              p.category === "combo"
                                ? "bg-violet-100 text-violet-700"
                                : "bg-blue-100 text-blue-700"
                            }`}
                          >
                            {p.category === "combo" ? "Combo" : "Producto"}
                          </span>
                          <span>{p.quantity} und.</span>
                          <span>${p.revenue.toFixed(2)}</span>
                        </div>
                      </div>
                      <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
                        <div
                          className="h-full rounded-full bg-primary/60"
                          style={{ width: `${(p.quantity / maxQty) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-white p-4 shadow-sm">
      <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-1">{label}</p>
      <p className="text-2xl font-bold text-foreground">{value}</p>
    </div>
  );
}
