"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api";
import CustomerSearch, { CustomerInfo } from "@/components/pedido-telefonico/CustomerSearch";
import ProductPicker from "@/components/pedido-telefonico/ProductPicker";
import CartSummary, { CartItem } from "@/components/pedido-telefonico/CartSummary";
import { OrderOrigin } from "@/lib/types";

export default function PedidoTelefonicoPage() {
  const { pizzeria_id } = useParams<{ pizzeria_id: string }>();
  const router = useRouter();

  const [customer, setCustomer] = useState<CustomerInfo | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [origin, setOrigin] = useState<Extract<OrderOrigin, "phone" | "operator">>("phone");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ---- Acciones del carrito ----

  function handleAdd(item: CartItem) {
    setCart((prev) => {
      const existing = prev.find((i) => i.key === item.key);
      if (existing) {
        return prev.map((i) =>
          i.key === item.key ? { ...i, quantity: i.quantity + 1 } : i
        );
      }
      return [...prev, item];
    });
  }

  function handleQuantity(key: string, delta: number) {
    setCart((prev) =>
      prev
        .map((i) => (i.key === key ? { ...i, quantity: i.quantity + delta } : i))
        .filter((i) => i.quantity > 0)
    );
  }

  function handleNotes(key: string, itemNotes: string) {
    setCart((prev) =>
      prev.map((i) => (i.key === key ? { ...i, notes: itemNotes } : i))
    );
  }

  function handleRemove(key: string) {
    setCart((prev) => prev.filter((i) => i.key !== key));
  }

  // ---- Envío ----

  async function handleSubmit() {
    if (!customer) { setError("Seleccioná un cliente."); return; }
    if (cart.length === 0) { setError("Agregá al menos un ítem."); return; }

    setSubmitting(true); setError(null);
    try {
      const items = cart.map((i) => ({
        product_id: i.type === "product" ? i.ref_id : null,
        combo_id: i.type === "combo" ? i.ref_id : null,
        quantity: i.quantity,
        unit_price: i.unit_price,
        notes: i.notes || null,
      }));

      const order = await apiFetch<{ id: number }>(
        `/pizzerias/${pizzeria_id}/pedidos`,
        {
          method: "POST",
          body: JSON.stringify({
            customer_id: customer.id,
            origin,
            notes: notes || null,
            items,
          }),
        }
      );

      router.push(`/${pizzeria_id}/dashboard`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al crear el pedido");
    } finally {
      setSubmitting(false);
    }
  }

  const total = cart.reduce((s, i) => s + i.unit_price * i.quantity, 0);

  return (
    <div className="mx-auto max-w-screen-xl px-4 py-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-foreground">Nuevo pedido manual</h1>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">Origen:</label>
          <select
            value={origin}
            onChange={(e) => setOrigin(e.target.value as typeof origin)}
            className="rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="phone">📞 Telefónico</option>
            <option value="operator">🖥 Operador</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_380px]">
        {/* Columna izquierda */}
        <div className="space-y-8">
          {/* Paso 1 — Cliente */}
          <section className="rounded-lg border border-border bg-white p-5 space-y-4">
            {customer ? (
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Cliente seleccionado</p>
                  <p className="font-semibold">{customer.name ?? customer.phone}</p>
                  <p className="text-sm text-muted-foreground">
                    {customer.name ? customer.phone : ""}
                    {customer.address ? ` · ${customer.address}` : ""}
                  </p>
                </div>
                <button
                  onClick={() => setCustomer(null)}
                  className="text-sm text-primary hover:underline"
                >
                  Cambiar
                </button>
              </div>
            ) : (
              <CustomerSearch pizzeriaId={pizzeria_id} onSelect={setCustomer} />
            )}
          </section>

          {/* Paso 2 — Catálogo */}
          {customer && (
            <section className="rounded-lg border border-border bg-white p-5">
              <ProductPicker pizzeriaId={pizzeria_id} onAdd={handleAdd} />
            </section>
          )}
        </div>

        {/* Columna derecha — carrito */}
        <div className="space-y-4">
          <section className="rounded-lg border border-border bg-white p-5 space-y-4">
            <h3 className="font-semibold text-foreground">3. Resumen del pedido</h3>

            <CartSummary
              items={cart}
              onQuantityChange={handleQuantity}
              onNotesChange={handleNotes}
              onRemove={handleRemove}
            />

            {cart.length > 0 && (
              <>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Notas del pedido</label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={2}
                    placeholder="Instrucciones generales del pedido…"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                  />
                </div>

                {error && (
                  <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                    {error}
                  </p>
                )}

                <button
                  onClick={handleSubmit}
                  disabled={submitting || !customer}
                  className="w-full rounded-md bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-60 transition-colors"
                >
                  {submitting
                    ? "Creando pedido…"
                    : `Confirmar pedido · $${total.toFixed(2)}`}
                </button>
              </>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
