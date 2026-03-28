"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import ProductList from "@/components/menu/ProductList";
import ComboList from "@/components/menu/ComboList";
import PizzeriaConfigForm from "@/components/menu/PizzeriaConfigForm";

type Tab = "productos" | "combos" | "config";

const TABS: { id: Tab; label: string }[] = [
  { id: "productos", label: "Productos" },
  { id: "combos", label: "Combos" },
  { id: "config", label: "Configuración" },
];

export default function MenuPage() {
  const { pizzeria_id } = useParams<{ pizzeria_id: string }>();
  const [activeTab, setActiveTab] = useState<Tab>("productos");

  return (
    <div className="mx-auto max-w-screen-lg px-4 py-6 space-y-6">
      <h1 className="text-xl font-bold text-foreground">Menú y catálogo</h1>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg border border-border bg-white p-1 w-fit">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-secondary"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Contenido del tab activo */}
      {activeTab === "productos" && <ProductList pizzeriaId={pizzeria_id} />}
      {activeTab === "combos" && <ComboList pizzeriaId={pizzeria_id} />}
      {activeTab === "config" && <PizzeriaConfigForm pizzeriaId={pizzeria_id} />}
    </div>
  );
}
