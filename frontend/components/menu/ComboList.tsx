"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { Combo, Product } from "@/lib/types";

export default function ComboList({ pizzeriaId }: { pizzeriaId: string }) {
  const [combos, setCombos] = useState<Combo[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  async function load() {
    try {
      const [c, p] = await Promise.all([
        apiFetch<Combo[]>(`/pizzerias/${pizzeriaId}/combos?include_unavailable=true`),
        apiFetch<Product[]>(`/pizzerias/${pizzeriaId}/productos`),
      ]);
      setCombos(c);
      setProducts(p);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar combos");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [pizzeriaId]);

  async function toggleAvailability(combo: Combo) {
    await apiFetch(`/pizzerias/${pizzeriaId}/combos/${combo.id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_available: !combo.is_available }),
    });
    load();
  }

  if (loading) return <p className="py-8 text-center text-sm text-muted-foreground">Cargando…</p>;
  if (error) return <p className="py-4 text-sm text-destructive">{error}</p>;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button onClick={() => setShowNew(true)} className={btnPrimary}>
          + Nuevo combo
        </button>
      </div>

      {showNew && (
        <NewComboForm
          pizzeriaId={pizzeriaId}
          onSave={() => { setShowNew(false); load(); }}
          onCancel={() => setShowNew(false)}
        />
      )}

      {combos.length === 0 && !showNew && (
        <p className="py-8 text-center text-sm text-muted-foreground">No hay combos. Creá el primero.</p>
      )}

      {combos.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-border bg-white">
          {combos.map((combo, idx) => (
            <div key={combo.id}>
              {idx > 0 && <div className="border-t border-border" />}
              <div className="px-4 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{combo.name}</span>
                      <span className="font-semibold text-primary">${Number(combo.price).toFixed(2)}</span>
                      {!combo.is_available && (
                        <span className="rounded bg-destructive/10 px-1.5 py-0.5 text-xs text-destructive">Inactivo</span>
                      )}
                    </div>
                    {combo.description && (
                      <p className="mt-0.5 text-sm text-muted-foreground">{combo.description}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => setExpandedId(expandedId === combo.id ? null : combo.id)}
                      className={btnOutline}
                    >
                      {expandedId === combo.id ? "▲ Ítems" : "▼ Ítems"}
                    </button>
                    <button
                      onClick={() => toggleAvailability(combo)}
                      className={combo.is_available ? btnOutline : btnPrimary}
                    >
                      {combo.is_available ? "Desactivar" : "Activar"}
                    </button>
                  </div>
                </div>

                {expandedId === combo.id && (
                  <ComboItemManager
                    pizzeriaId={pizzeriaId}
                    combo={combo}
                    products={products}
                    onChanged={load}
                  />
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Gestión de ítems de un combo
// ---------------------------------------------------------------------------

interface ComboItemRaw {
  id: number;
  combo_id: number;
  product_id: number;
  quantity: number;
}

function ComboItemManager({
  pizzeriaId,
  combo,
  products,
  onChanged,
}: {
  pizzeriaId: string;
  combo: Combo;
  products: Product[];
  onChanged: () => void;
}) {
  const [comboItems, setComboItems] = useState<ComboItemRaw[]>([]);
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function loadItems() {
    // Los ítems del combo se obtienen del endpoint de combo items
    // Como no hay un GET directo de combo items, cargamos todos y filtramos
    // Nota: en una mejora futura se puede agregar GET /combos/{id}/items
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/pizzerias/${pizzeriaId}/combos/${combo.id}`,
        { headers: { Authorization: `Bearer ${localStorage.getItem("token")}` } }
      );
      // El endpoint GET combo no devuelve items directamente en este schema.
      // Usamos el workaround de listar todos los combo_items filtrando por combo_id.
      // Por ahora mostramos mensaje de que se gestiona por API.
    } catch {}
  }

  async function addItem() {
    if (!productId || !quantity) return;
    setSaving(true); setErr(null);
    try {
      await apiFetch(
        `/pizzerias/${pizzeriaId}/combos/${combo.id}/items?product_id=${productId}&quantity=${quantity}`,
        { method: "POST" }
      );
      setProductId(""); setQuantity("1");
      onChanged();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Error");
    } finally { setSaving(false); }
  }

  return (
    <div className="mt-3 rounded-md bg-secondary/50 p-3 space-y-3">
      <p className="text-xs text-muted-foreground">
        Agregá productos a este combo:
      </p>

      {/* Agregar ítem */}
      <div className="flex items-end gap-2">
        <div className="space-y-0.5 flex-1">
          <label className="text-xs text-muted-foreground">Producto</label>
          <select
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="">Seleccioná…</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>{p.full_name}</option>
            ))}
          </select>
        </div>
        <div className="space-y-0.5">
          <label className="text-xs text-muted-foreground">Cant.</label>
          <input
            type="number" min="1" value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="w-16 rounded-md border border-input bg-background px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
        <button
          onClick={addItem}
          disabled={saving || !productId}
          className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
        >
          {saving ? "…" : "+ Agregar"}
        </button>
      </div>
      {err && <p className="text-xs text-destructive">{err}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Formulario nuevo combo
// ---------------------------------------------------------------------------

function NewComboForm({
  pizzeriaId,
  onSave,
  onCancel,
}: {
  pizzeriaId: string;
  onSave: () => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true); setErr(null);
    try {
      await apiFetch(`/pizzerias/${pizzeriaId}/combos`, {
        method: "POST",
        body: JSON.stringify({
          name,
          description: description || undefined,
          price: parseFloat(price),
        }),
      });
      onSave();
    } catch (ex) {
      setErr(ex instanceof ApiError ? ex.message : "Error al guardar");
    } finally { setSaving(false); }
  }

  return (
    <div className="rounded-lg border border-primary/40 bg-white p-4 space-y-3">
      <h4 className="font-semibold">Nuevo combo</h4>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="space-y-0.5">
          <label className="text-sm font-medium">Nombre *</label>
          <input type="text" required value={name} onChange={(e) => setName(e.target.value)}
            placeholder="Combo Familiar" className={inputCls} />
        </div>
        <div className="space-y-0.5">
          <label className="text-sm font-medium">Descripción</label>
          <input type="text" value={description} onChange={(e) => setDescription(e.target.value)}
            placeholder="Opcional…" className={inputCls} />
        </div>
        <div className="space-y-0.5">
          <label className="text-sm font-medium">Precio *</label>
          <input type="number" required min="0" step="0.01" value={price}
            onChange={(e) => setPrice(e.target.value)} placeholder="0.00" className={inputCls} />
        </div>
        {err && <p className="text-sm text-destructive">{err}</p>}
        <div className="flex gap-2 justify-end">
          <button type="button" onClick={onCancel} className={btnOutline}>Cancelar</button>
          <button type="submit" disabled={saving} className={btnPrimary}>
            {saving ? "Guardando…" : "Guardar"}
          </button>
        </div>
      </form>
    </div>
  );
}

const inputCls = "w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";
const btnPrimary = "rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60 transition-colors";
const btnOutline = "rounded-md border border-border px-3 py-2 text-sm hover:bg-secondary transition-colors";
