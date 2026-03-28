"use client";

import { ProductSize } from "@/lib/types";

export interface CartItem {
  key: string;
  type: "product" | "combo";
  ref_id: number;
  catalog_item_id?: number;
  name: string;
  size?: ProductSize;
  unit_price: number;
  quantity: number;
  notes?: string;
}

const SIZE_LABEL: Record<ProductSize, string> = { large: "Grande", small: "Chica" };

interface Props {
  items: CartItem[];
  onQuantityChange: (key: string, delta: number) => void;
  onNotesChange: (key: string, notes: string) => void;
  onRemove: (key: string) => void;
}

export default function CartSummary({
  items,
  onQuantityChange,
  onNotesChange,
  onRemove,
}: Props) {
  const total = items.reduce((sum, i) => sum + i.unit_price * i.quantity, 0);

  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
        Agregá ítems desde el catálogo
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div
          key={item.key}
          className="rounded-lg border border-border bg-white p-3 space-y-2"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm truncate">
                {item.name}
                {item.size ? ` (${SIZE_LABEL[item.size]})` : ""}
              </p>
              <p className="text-xs text-muted-foreground">
                ${item.unit_price.toFixed(2)} c/u
              </p>
            </div>

            {/* Cantidad */}
            <div className="flex items-center gap-1 flex-shrink-0">
              <button
                onClick={() => onQuantityChange(item.key, -1)}
                className="h-6 w-6 rounded border border-border text-sm hover:bg-secondary transition-colors"
              >
                −
              </button>
              <span className="w-6 text-center text-sm font-medium">{item.quantity}</span>
              <button
                onClick={() => onQuantityChange(item.key, +1)}
                className="h-6 w-6 rounded border border-border text-sm hover:bg-secondary transition-colors"
              >
                +
              </button>
              <button
                onClick={() => onRemove(item.key)}
                className="ml-1 h-6 w-6 rounded text-destructive hover:bg-destructive/10 transition-colors text-xs"
                title="Eliminar"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Subtotal */}
          <div className="flex items-center justify-between">
            <input
              type="text"
              value={item.notes ?? ""}
              onChange={(e) => onNotesChange(item.key, e.target.value)}
              placeholder="Notas (sin cebolla, bien cocido…)"
              className="flex-1 rounded border border-input bg-background px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
            />
            <span className="ml-3 flex-shrink-0 text-sm font-semibold">
              ${(item.unit_price * item.quantity).toFixed(2)}
            </span>
          </div>
        </div>
      ))}

      {/* Total */}
      <div className="flex justify-between rounded-lg bg-primary/5 px-4 py-3 font-semibold">
        <span>Total</span>
        <span className="text-primary">${total.toFixed(2)}</span>
      </div>
    </div>
  );
}
