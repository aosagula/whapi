"use client";

import { Order } from "@/lib/types";
import OrderCard from "./OrderCard";

interface ColumnDef {
  status: string;
  label: string;
  nextStatus: string | null;
  nextLabel: string | null;
  color: string;
}

interface Props {
  column: ColumnDef;
  orders: Order[];
  onAdvance: (orderId: number, targetStatus: string) => void;
  onCancel: (orderId: number) => void;
  advancingId: number | null;
}

export default function KanbanColumn({
  column,
  orders,
  onAdvance,
  onCancel,
  advancingId,
}: Props) {
  return (
    <div className="flex flex-col min-w-[220px] w-[220px] flex-shrink-0">
      {/* Encabezado de columna */}
      <div className={`flex items-center justify-between rounded-t-lg px-3 py-2 ${column.color}`}>
        <span className="text-sm font-semibold">{column.label}</span>
        <span className="rounded-full bg-white/60 px-2 py-0.5 text-xs font-bold">
          {orders.length}
        </span>
      </div>

      {/* Tarjetas */}
      <div className="flex-1 rounded-b-lg bg-secondary/50 p-2 space-y-2 min-h-[120px]">
        {orders.length === 0 && (
          <p className="py-4 text-center text-xs text-muted-foreground">Sin pedidos</p>
        )}
        {orders.map((order) => (
          <OrderCard
            key={order.id}
            order={order}
            nextStatus={column.nextStatus}
            nextLabel={column.nextLabel}
            onAdvance={(id) =>
              column.nextStatus ? onAdvance(id, column.nextStatus) : undefined
            }
            onCancel={onCancel}
            advancing={advancingId === order.id}
          />
        ))}
      </div>
    </div>
  );
}
