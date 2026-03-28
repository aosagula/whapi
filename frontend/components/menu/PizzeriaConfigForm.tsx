"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { PizzeriaConfig } from "@/lib/types";

export default function PizzeriaConfigForm({ pizzeriaId }: { pizzeriaId: string }) {
  const [config, setConfig] = useState<PizzeriaConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Campos editables
  const [surcharge, setSurcharge] = useState("");
  const [welcome, setWelcome] = useState("");
  const [opening, setOpening] = useState("");
  const [closing, setClosing] = useState("");

  useEffect(() => {
    apiFetch<PizzeriaConfig>(`/pizzerias/${pizzeriaId}/config`)
      .then((c) => {
        setConfig(c);
        setSurcharge(String(c.half_half_surcharge ?? 0));
        setWelcome(c.welcome_message ?? "");
        setOpening(c.opening_time ?? "");
        setClosing(c.closing_time ?? "");
      })
      .catch((err) => {
        // 404 = config no creada aún (se crea con upsert en pizzerias.py)
        if (err instanceof ApiError && err.status === 404) {
          setSurcharge("0");
        } else {
          setError(err instanceof ApiError ? err.message : "Error al cargar configuración");
        }
      })
      .finally(() => setLoading(false));
  }, [pizzeriaId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true); setError(null); setSuccess(false);
    try {
      const updated = await apiFetch<PizzeriaConfig>(
        `/pizzerias/${pizzeriaId}/config`,
        {
          method: "PATCH",
          body: JSON.stringify({
            half_half_surcharge: parseFloat(surcharge) || 0,
            welcome_message: welcome || null,
            opening_time: opening || null,
            closing_time: closing || null,
          }),
        }
      );
      setConfig(updated);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally { setSaving(false); }
  }

  if (loading) return <p className="py-8 text-center text-sm text-muted-foreground">Cargando…</p>;

  return (
    <div className="max-w-lg">
      <form onSubmit={handleSubmit} className="space-y-5 rounded-lg border border-border bg-white p-6">
        <h3 className="font-semibold text-foreground">Configuración operativa</h3>

        <div className="space-y-1">
          <label className="text-sm font-medium">
            Recargo pizza mitad y mitad ($)
          </label>
          <p className="text-xs text-muted-foreground">
            Se suma al precio mayor de las dos mitades.
          </p>
          <input
            type="number"
            min="0"
            step="0.01"
            value={surcharge}
            onChange={(e) => setSurcharge(e.target.value)}
            className={inputCls}
          />
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium">Mensaje de bienvenida</label>
          <p className="text-xs text-muted-foreground">
            Texto que el chatbot envía al iniciar una conversación.
          </p>
          <textarea
            rows={3}
            value={welcome}
            onChange={(e) => setWelcome(e.target.value)}
            placeholder="¡Hola! Bienvenido a nuestra pizzería. ¿En qué te puedo ayudar?"
            className={`${inputCls} resize-none`}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="text-sm font-medium">Horario apertura</label>
            <input
              type="time"
              value={opening}
              onChange={(e) => setOpening(e.target.value)}
              className={inputCls}
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Horario cierre</label>
            <input
              type="time"
              value={closing}
              onChange={(e) => setClosing(e.target.value)}
              className={inputCls}
            />
          </div>
        </div>

        {error && (
          <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
        )}
        {success && (
          <p className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
            ✓ Configuración guardada
          </p>
        )}

        <button type="submit" disabled={saving} className={btnPrimary}>
          {saving ? "Guardando…" : "Guardar cambios"}
        </button>
      </form>
    </div>
  );
}

const inputCls = "w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";
const btnPrimary = "rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60 transition-colors";
