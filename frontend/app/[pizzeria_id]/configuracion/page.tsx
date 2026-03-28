"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import WhatsAppManager from "@/components/configuracion/WhatsAppManager";
import EmpleadoManager from "@/components/configuracion/EmpleadoManager";

type Tab = "whatsapp" | "empleados";

const TABS: { id: Tab; label: string }[] = [
  { id: "whatsapp", label: "📱 WhatsApp" },
  { id: "empleados", label: "👥 Empleados" },
];

export default function ConfiguracionPage() {
  const { pizzeria_id } = useParams<{ pizzeria_id: string }>();
  const [activeTab, setActiveTab] = useState<Tab>("whatsapp");

  return (
    <div className="mx-auto max-w-screen-lg px-4 py-6 space-y-6">
      <h1 className="text-xl font-bold text-foreground">Configuración</h1>

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

      {activeTab === "whatsapp" && (
        <section>
          <p className="mb-4 text-sm text-muted-foreground">
            Administrá los números de WhatsApp conectados a esta pizzería.
            Cada número corresponde a una sesión en WPPConnect.
          </p>
          <WhatsAppManager pizzeriaId={pizzeria_id} />
        </section>
      )}

      {activeTab === "empleados" && (
        <section>
          <p className="mb-4 text-sm text-muted-foreground">
            Invitá empleados y asignales un rol. Podés cambiar el rol haciendo clic
            en la etiqueta del rol. Los empleados acceden con su propio usuario y contraseña.
          </p>
          <EmpleadoManager pizzeriaId={pizzeria_id} />
        </section>
      )}
    </div>
  );
}
