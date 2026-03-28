"use client";

import { Order, OrderOrigin } from "@/lib/types";

interface Props {
  order: Order;
  nextStatus: string | null;
  nextLabel: string | null;
  onAdvance: (orderId: number) => void;
  onCancel: (orderId: number) => void;
  advancing: boolean;
}

const ORIGIN_LABEL: Record<OrderOrigin, string> = {
  whatsapp: "💬 WA",
  phone: "📞 Tel",
  operator: "🖥 Op",
};

export default function OrderCard({
  order,
  nextStatus,
  nextLabel,
  onAdvance,
  onCancel,
  advancing,
}: Props) {
  const elapsed = formatElapsed(order.created_at);
  const isUrgent = minutesSince(order.created_at) > 20;

  return (
    <div
      className={`rounded-lg border bg-white p-3 shadow-sm space-y-2 text-sm transition-opacity ${
        advancing ? "opacity-50" : ""
      } ${isUrgent ? "border-destructive/50" : "border-border"}`}
    >
      {/* Cabecera */}
      <div className="flex items-center justify-between">
        <span className="font-semibold text-foreground">#{order.id}</span>
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">
            {ORIGIN_LABEL[order.origin]}
          </span>
          <span
            className={`text-xs font-medium ${
              isUrgent ? "text-destructive" : "text-muted-foreground"
            }`}
          >
            {elapsed}
          </span>
        </div>
      </div>

      {/* Ítems */}
      <ul className="space-y-0.5 text-xs text-muted-foreground">
        {order.items.slice(0, 3).map((item) => (
          <li key={item.id} className="flex justify-between">
            <span>
              {item.quantity}× {item.product_id ? `Prod.${item.product_id}` : `Combo ${item.combo_id}`}
            </span>
            <span>${(item.unit_price * item.quantity).toFixed(2)}</span>
          </li>
        ))}
        {order.items.length > 3 && (
          <li className="text-muted-foreground/70">+{order.items.length - 3} más…</li>
        )}
      </ul>

      {/* Notas */}
      {order.notes && (
        <p className="text-xs text-muted-foreground italic truncate">{order.notes}</p>
      )}

      {/* Total */}
      <div className="flex items-center justify-between border-t border-border pt-2">
        <span className="text-xs text-muted-foreground">Total</span>
        <span className="font-semibold">${Number(order.total).toFixed(2)}</span>
      </div>

      {/* Acciones */}
      <div className="flex gap-1.5 pt-1">
        {nextStatus && nextLabel && (
          <button
            onClick={() => onAdvance(order.id)}
            disabled={advancing}
            className="flex-1 rounded-md bg-primary px-2 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {nextLabel} →
          </button>
        )}
        <button
          onClick={() => onCancel(order.id)}
          disabled={advancing}
          className="rounded-md border border-destructive/40 px-2 py-1.5 text-xs font-medium text-destructive hover:bg-destructive/10 disabled:opacity-50 transition-colors"
          title="Cancelar pedido"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

function minutesSince(isoDate: string): number {
  return Math.floor((Date.now() - new Date(isoDate).getTime()) / 60000);
}

function formatElapsed(isoDate: string): string {
  const mins = minutesSince(isoDate);
  if (mins < 60) return `${mins}m`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${h}h${m > 0 ? ` ${m}m` : ""}`;
}
