"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Product, CatalogItem, Combo, ProductCategory, ProductSize } from "@/lib/types";
import { CartItem } from "./CartSummary";

const CATEGORY_LABEL: Record<ProductCategory, string> = {
  pizza: "🍕 Pizzas",
  empanada: "🥟 Empanadas",
  drink: "🥤 Bebidas",
};

const SIZE_LABEL: Record<ProductSize, string> = {
  large: "Grande",
  small: "Chica",
};

interface Props {
  pizzeriaId: string;
  onAdd: (item: CartItem) => void;
}

export default function ProductPicker({ pizzeriaId, onAdd }: Props) {
  const [products, setProducts] = useState<Product[]>([]);
  const [catalogItems, setCatalogItems] = useState<CatalogItem[]>([]);
  const [combos, setCombos] = useState<Combo[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"products" | "combos">("products");

  useEffect(() => {
    Promise.all([
      apiFetch<Product[]>(`/pizzerias/${pizzeriaId}/productos`),
      apiFetch<CatalogItem[]>(`/pizzerias/${pizzeriaId}/catalog-items`),
      apiFetch<Combo[]>(`/pizzerias/${pizzeriaId}/combos`),
    ]).then(([prods, items, combos]) => {
      setProducts(prods);
      setCatalogItems(items);
      setCombos(combos);
    }).finally(() => setLoading(false));
  }, [pizzeriaId]);

  function itemsForProduct(productId: number) {
    return catalogItems.filter((i) => i.product_id === productId && i.is_active);
  }

  function handleAddProduct(product: Product, catalogItem: CatalogItem) {
    onAdd({
      key: `product-${product.id}-${catalogItem.id}`,
      type: "product",
      ref_id: product.id,
      catalog_item_id: catalogItem.id,
      name: product.full_name,
      size: catalogItem.size ?? undefined,
      unit_price: Number(catalogItem.price),
      quantity: 1,
    });
  }

  function handleAddCombo(combo: Combo) {
    onAdd({
      key: `combo-${combo.id}`,
      type: "combo",
      ref_id: combo.id,
      name: combo.name,
      unit_price: Number(combo.price),
      quantity: 1,
    });
  }

  if (loading) return <p className="py-4 text-sm text-muted-foreground">Cargando catálogo…</p>;

  return (
    <div className="space-y-3">
      <h3 className="font-semibold text-foreground">2. Agregar ítems</h3>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg border border-border bg-white p-1 w-fit text-sm">
        {(["products", "combos"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`rounded-md px-3 py-1.5 font-medium transition-colors ${
              activeTab === t
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-secondary"
            }`}
          >
            {t === "products" ? "Productos" : "Combos"}
          </button>
        ))}
      </div>

      {/* Productos */}
      {activeTab === "products" && (
        <div className="space-y-4">
          {(["pizza", "empanada", "drink"] as ProductCategory[]).map((cat) => {
            const catProds = products.filter((p) => p.category === cat);
            if (catProds.length === 0) return null;
            return (
              <section key={cat}>
                <h4 className="mb-2 text-sm font-medium text-muted-foreground">
                  {CATEGORY_LABEL[cat]}
                </h4>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {catProds.map((product) => {
                    const prices = itemsForProduct(product.id);
                    if (prices.length === 0) return null;
                    return (
                      <div
                        key={product.id}
                        className="rounded-lg border border-border bg-white p-3 space-y-2"
                      >
                        <p className="font-medium text-sm">{product.full_name}</p>
                        <div className="flex flex-wrap gap-1.5">
                          {prices.map((ci) => (
                            <button
                              key={ci.id}
                              onClick={() => handleAddProduct(product, ci)}
                              className="rounded-md border border-primary/40 px-2.5 py-1 text-xs font-medium text-primary hover:bg-primary/10 transition-colors"
                            >
                              {ci.size ? `${SIZE_LABEL[ci.size]} ` : ""}
                              ${Number(ci.price).toFixed(2)}
                            </button>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            );
          })}
          {products.length === 0 && (
            <p className="text-sm text-muted-foreground">Sin productos disponibles.</p>
          )}
        </div>
      )}

      {/* Combos */}
      {activeTab === "combos" && (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {combos.map((combo) => (
            <button
              key={combo.id}
              onClick={() => handleAddCombo(combo)}
              className="rounded-lg border border-border bg-white p-3 text-left hover:border-primary/50 hover:shadow-sm transition-all"
            >
              <p className="font-medium text-sm">{combo.name}</p>
              {combo.description && (
                <p className="text-xs text-muted-foreground mt-0.5">{combo.description}</p>
              )}
              <p className="mt-1.5 font-semibold text-primary text-sm">
                ${Number(combo.price).toFixed(2)}
              </p>
            </button>
          ))}
          {combos.length === 0 && (
            <p className="text-sm text-muted-foreground">Sin combos disponibles.</p>
          )}
        </div>
      )}
    </div>
  );
}
