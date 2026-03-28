"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { WhatsAppNumber, WhatsAppSessionStatus } from "@/lib/types";

const STATUS_LABEL: Record<WhatsAppSessionStatus, string> = {
  connected: "Conectado",
  disconnected: "Desconectado",
  scanning_qr: "Esperando QR",
};

const STATUS_COLOR: Record<WhatsAppSessionStatus, string> = {
  connected: "bg-green-100 text-green-700",
  disconnected: "bg-secondary text-muted-foreground",
  scanning_qr: "bg-yellow-100 text-yellow-700",
};

export default function WhatsAppManager({ pizzeriaId }: { pizzeriaId: string }) {
  const [numbers, setNumbers] = useState<WhatsAppNumber[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const [number, setNumber] = useState("");
  const [sessionName, setSessionName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  async function load() {
    try {
      const data = await apiFetch<WhatsAppNumber[]>(
        `/pizzerias/${pizzeriaId}/whatsapp`
      );
      setNumbers(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar números");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [pizzeriaId]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true); setSaveError(null);
    try {
      await apiFetch(`/pizzerias/${pizzeriaId}/whatsapp`, {
        method: "POST",
        body: JSON.stringify({ number, session_name: sessionName }),
      });
      setNumber(""); setSessionName(""); setShowForm(false);
      load();
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Error al agregar número");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate(numberId: number) {
    if (!confirm("¿Desactivar este número de WhatsApp?")) return;
    try {
      await apiFetch(`/pizzerias/${pizzeriaId}/whatsapp/${numberId}`, {
        method: "DELETE",
      });
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al desactivar");
    }
  }

  if (loading) return <p className="py-8 text-center text-sm text-muted-foreground">Cargando…</p>;

  return (
    <div className="space-y-4 max-w-2xl">
      {error && (
        <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
      )}

      {/* Lista */}
      {numbers.length === 0 && !showForm && (
        <p className="py-6 text-center text-sm text-muted-foreground">
          No hay números de WhatsApp registrados.
        </p>
      )}

      {numbers.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-border bg-white">
          {numbers.map((n, idx) => (
            <div key={n.id}>
              {idx > 0 && <div className="border-t border-border" />}
              <div className="flex items-center justify-between px-4 py-4 gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium">{n.number}</span>
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLOR[n.status]}`}>
                      {STATUS_LABEL[n.status]}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Sesión: <code className="bg-secondary px-1 rounded">{n.session_name}</code>
                  </p>
                </div>
                <button
                  onClick={() => handleDeactivate(n.id)}
                  className="flex-shrink-0 rounded-md border border-destructive/40 px-3 py-1.5 text-xs text-destructive hover:bg-destructive/10 transition-colors"
                >
                  Desactivar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Formulario nuevo número */}
      {showForm ? (
        <form
          onSubmit={handleAdd}
          className="rounded-lg border border-primary/40 bg-white p-4 space-y-3"
        >
          <h4 className="font-semibold text-sm">Nuevo número de WhatsApp</h4>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-sm font-medium">Número *</label>
              <input
                type="text"
                required
                value={number}
                onChange={(e) => setNumber(e.target.value)}
                placeholder="5491112345678"
                className={inputCls}
              />
              <p className="text-xs text-muted-foreground">Sin + ni espacios</p>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Nombre de sesión *</label>
              <input
                type="text"
                required
                value={sessionName}
                onChange={(e) => setSessionName(e.target.value)}
                placeholder="pizzeria-norte"
                className={inputCls}
              />
              <p className="text-xs text-muted-foreground">Único en el sistema</p>
            </div>
          </div>

          {saveError && (
            <p className="text-sm text-destructive">{saveError}</p>
          )}

          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => { setShowForm(false); setSaveError(null); }}
              className={btnOutline}
            >
              Cancelar
            </button>
            <button type="submit" disabled={saving} className={btnPrimary}>
              {saving ? "Guardando…" : "Agregar número"}
            </button>
          </div>
        </form>
      ) : (
        <button onClick={() => setShowForm(true)} className={btnPrimary}>
          + Agregar número de WhatsApp
        </button>
      )}
    </div>
  );
}

const inputCls =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";
const btnPrimary =
  "rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60 transition-colors";
const btnOutline =
  "rounded-md border border-border px-4 py-2 text-sm hover:bg-secondary transition-colors";
