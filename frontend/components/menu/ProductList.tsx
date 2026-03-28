"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { Product, CatalogItem, ProductCategory, ProductSize } from "@/lib/types";

const CATEGORY_LABEL: Record<ProductCategory, string> = {
  pizza: "🍕 Pizzas",
  empanada: "🥟 Empanadas",
  drink: "🥤 Bebidas",
};

const SIZE_LABEL: Record<ProductSize, string> = {
  large: "Grande",
  small: "Chica",
};

export default function ProductList({ pizzeriaId }: { pizzeriaId: string }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [showNewProduct, setShowNewProduct] = useState(false);

  async function load() {
    try {
      const [prods, catItems] = await Promise.all([
        apiFetch<Product[]>(`/pizzerias/${pizzeriaId}/productos?include_unavailable=true`),
        apiFetch<CatalogItem[]>(`/pizzerias/${pizzeriaId}/catalog-items`),
      ]);
      setProducts(prods);
      setItems(catItems);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar productos");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [pizzeriaId]);

  async function toggleAvailability(product: Product) {
    await apiFetch(`/pizzerias/${pizzeriaId}/productos/${product.id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_available: !product.is_available }),
    });
    load();
  }

  const categories: ProductCategory[] = ["pizza", "empanada", "drink"];

  if (loading) return <p className="py-8 text-center text-sm text-muted-foreground">Cargando…</p>;
  if (error) return <p className="py-4 text-sm text-destructive">{error}</p>;

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <button onClick={() => setShowNewProduct(true)} className={btnPrimary}>
          + Nuevo producto
        </button>
      </div>

      {showNewProduct && (
        <NewProductForm
          pizzeriaId={pizzeriaId}
          onSave={() => { setShowNewProduct(false); load(); }}
          onCancel={() => setShowNewProduct(false)}
        />
      )}

      {categories.map((cat) => {
        const catProds = products.filter((p) => p.category === cat);
        if (catProds.length === 0) return null;
        return (
          <section key={cat}>
            <h3 className="mb-2 font-semibold text-foreground">{CATEGORY_LABEL[cat]}</h3>
            <div className="overflow-hidden rounded-lg border border-border bg-white">
              {catProds.map((product, idx) => (
                <div key={product.id}>
                  {idx > 0 && <div className="border-t border-border" />}
                  <div className="px-4 py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{product.full_name}</span>
                          <span className="rounded bg-secondary px-1.5 py-0.5 text-xs text-muted-foreground">
                            {product.code}
                          </span>
                          {!product.is_available && (
                            <span className="rounded bg-destructive/10 px-1.5 py-0.5 text-xs text-destructive">
                              Inactivo
                            </span>
                          )}
                        </div>
                        {product.description && (
                          <p className="mt-0.5 text-sm text-muted-foreground truncate">
                            {product.description}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <button
                          onClick={() => setExpandedId(expandedId === product.id ? null : product.id)}
                          className={btnOutline}
                        >
                          {expandedId === product.id ? "▲ Precios" : "▼ Precios"}
                        </button>
                        <button
                          onClick={() => toggleAvailability(product)}
                          className={product.is_available ? btnOutline : btnPrimary}
                        >
                          {product.is_available ? "Desactivar" : "Activar"}
                        </button>
                      </div>
                    </div>

                    {expandedId === product.id && (
                      <PriceManager
                        pizzeriaId={pizzeriaId}
                        product={product}
                        items={items.filter((i) => i.product_id === product.id)}
                        onChanged={load}
                      />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        );
      })}

      {products.length === 0 && (
        <p className="py-8 text-center text-sm text-muted-foreground">
          No hay productos. Creá el primero.
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Gestión de precios / variantes
// ---------------------------------------------------------------------------

function PriceManager({
  pizzeriaId,
  product,
  items,
  onChanged,
}: {
  pizzeriaId: string;
  product: Product;
  items: CatalogItem[];
  onChanged: () => void;
}) {
  const [price, setPrice] = useState("");
  const [size, setSize] = useState<ProductSize | "">("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function addItem() {
    if (!price) return;
    setSaving(true); setErr(null);
    try {
      await apiFetch(`/pizzerias/${pizzeriaId}/catalog-items`, {
        method: "POST",
        body: JSON.stringify({
          product_id: product.id,
          size: size || null,
          price: parseFloat(price),
        }),
      });
      setPrice(""); setSize("");
      onChanged();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Error");
    } finally { setSaving(false); }
  }

  async function toggleItem(item: CatalogItem) {
    await apiFetch(`/pizzerias/${pizzeriaId}/catalog-items/${item.id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !item.is_active }),
    });
    onChanged();
  }

  async function deleteItem(item: CatalogItem) {
    if (!confirm("¿Eliminar esta variante de precio?")) return;
    await apiFetch(`/pizzerias/${pizzeriaId}/catalog-items/${item.id}`, { method: "DELETE" });
    onChanged();
  }

  return (
    <div className="mt-3 rounded-md bg-secondary/50 p-3 space-y-3">
      {/* Precios existentes */}
      {items.length === 0 && (
        <p className="text-xs text-muted-foreground">Sin precios cargados aún.</p>
      )}
      {items.map((item) => (
        <div key={item.id} className="flex items-center justify-between text-sm">
          <span>
            {item.size ? SIZE_LABEL[item.size] : "Sin variante"} —{" "}
            <strong>${Number(item.price).toFixed(2)}</strong>
            {!item.is_active && (
              <span className="ml-2 text-xs text-destructive">(inactivo)</span>
            )}
          </span>
          <div className="flex gap-1">
            <button onClick={() => toggleItem(item)} className={btnXs}>
              {item.is_active ? "Desact." : "Activar"}
            </button>
            <button onClick={() => deleteItem(item)} className={`${btnXs} text-destructive`}>
              Eliminar
            </button>
          </div>
        </div>
      ))}

      {/* Agregar precio */}
      <div className="flex items-end gap-2 pt-1 border-t border-border">
        {product.category === "pizza" && (
          <div className="space-y-0.5">
            <label className="text-xs text-muted-foreground">Tamaño</label>
            <select
              value={size}
              onChange={(e) => setSize(e.target.value as ProductSize | "")}
              className={inputXs}
            >
              <option value="">—</option>
              <option value="large">Grande</option>
              <option value="small">Chica</option>
            </select>
          </div>
        )}
        <div className="space-y-0.5">
          <label className="text-xs text-muted-foreground">Precio $</label>
          <input
            type="number"
            min="0"
            step="0.01"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="0.00"
            className={inputXs}
          />
        </div>
        <button onClick={addItem} disabled={saving || !price} className={`${btnPrimary} text-xs py-1.5`}>
          {saving ? "…" : "+ Agregar"}
        </button>
      </div>
      {err && <p className="text-xs text-destructive">{err}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Formulario nuevo producto
// ---------------------------------------------------------------------------

function NewProductForm({
  pizzeriaId,
  onSave,
  onCancel,
}: {
  pizzeriaId: string;
  onSave: () => void;
  onCancel: () => void;
}) {
  const [code, setCode] = useState("");
  const [shortName, setShortName] = useState("");
  const [fullName, setFullName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<ProductCategory>("pizza");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true); setErr(null);
    try {
      await apiFetch(`/pizzerias/${pizzeriaId}/productos`, {
        method: "POST",
        body: JSON.stringify({ code, short_name: shortName, full_name: fullName, description: description || undefined, category }),
      });
      onSave();
    } catch (ex) {
      setErr(ex instanceof ApiError ? ex.message : "Error al guardar");
    } finally { setSaving(false); }
  }

  return (
    <div className="rounded-lg border border-primary/40 bg-white p-4 space-y-3">
      <h4 className="font-semibold">Nuevo producto</h4>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <LabeledInput label="Código *" value={code} onChange={setCode} placeholder="PIZZA-MUZA" required />
          <LabeledInput label="Nombre corto *" value={shortName} onChange={setShortName} placeholder="Muzarella" required />
        </div>
        <LabeledInput label="Nombre completo *" value={fullName} onChange={setFullName} placeholder="Pizza de Muzarella" required />
        <LabeledInput label="Descripción" value={description} onChange={setDescription} placeholder="Opcional…" />
        <div className="space-y-0.5">
          <label className="text-sm font-medium">Categoría *</label>
          <select value={category} onChange={(e) => setCategory(e.target.value as ProductCategory)} className={inputCls}>
            <option value="pizza">Pizza</option>
            <option value="empanada">Empanada</option>
            <option value="drink">Bebida</option>
          </select>
        </div>
        {err && <p className="text-sm text-destructive">{err}</p>}
        <div className="flex gap-2 justify-end">
          <button type="button" onClick={onCancel} className={btnOutline}>Cancelar</button>
          <button type="submit" disabled={saving} className={btnPrimary}>{saving ? "Guardando…" : "Guardar"}</button>
        </div>
      </form>
    </div>
  );
}

function LabeledInput({ label, value, onChange, placeholder, required }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; required?: boolean;
}) {
  return (
    <div className="space-y-0.5">
      <label className="text-sm font-medium">{label}</label>
      <input type="text" required={required} value={value} onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder} className={inputCls} />
    </div>
  );
}

const inputCls = "w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";
const inputXs = "rounded-md border border-input bg-background px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring w-24";
const btnPrimary = "rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60 transition-colors";
const btnOutline = "rounded-md border border-border px-3 py-2 text-sm hover:bg-secondary transition-colors";
const btnXs = "rounded border border-border px-2 py-0.5 text-xs hover:bg-secondary transition-colors";
