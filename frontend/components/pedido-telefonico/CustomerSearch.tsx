"use client";

import { useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";

export interface CustomerInfo {
  id: number;
  phone: string;
  name: string | null;
  address: string | null;
}

interface Props {
  pizzeriaId: string;
  onSelect: (customer: CustomerInfo) => void;
}

export default function CustomerSearch({ pizzeriaId, onSelect }: Props) {
  const [phone, setPhone] = useState("");
  const [results, setResults] = useState<CustomerInfo[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Campos para crear nuevo cliente
  const [newName, setNewName] = useState("");
  const [newAddress, setNewAddress] = useState("");
  const [creating, setCreating] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!phone.trim()) return;
    setLoading(true); setError(null); setSearched(false); setShowCreate(false);
    try {
      const data = await apiFetch<CustomerInfo[]>(
        `/pizzerias/${pizzeriaId}/clientes?search=${encodeURIComponent(phone.trim())}`
      );
      setResults(data);
      setSearched(true);
      setShowCreate(data.length === 0);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al buscar");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true); setError(null);
    try {
      const customer = await apiFetch<CustomerInfo>(
        `/pizzerias/${pizzeriaId}/clientes`,
        {
          method: "POST",
          body: JSON.stringify({
            phone: phone.trim(),
            name: newName || undefined,
            address: newAddress || undefined,
          }),
        }
      );
      onSelect(customer);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al crear cliente");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-foreground">1. Buscar cliente</h3>

      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="Teléfono o nombre…"
          className={inputCls + " flex-1"}
        />
        <button type="submit" disabled={loading} className={btnPrimary}>
          {loading ? "…" : "Buscar"}
        </button>
      </form>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {/* Resultados */}
      {searched && results.length > 0 && (
        <ul className="divide-y divide-border rounded-lg border border-border bg-white overflow-hidden">
          {results.map((c) => (
            <li key={c.id}>
              <button
                onClick={() => onSelect(c)}
                className="w-full px-4 py-3 text-left hover:bg-secondary transition-colors"
              >
                <p className="font-medium">{c.name ?? c.phone}</p>
                <p className="text-sm text-muted-foreground">
                  {c.name ? c.phone : ""}
                  {c.address ? ` · ${c.address}` : ""}
                </p>
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Crear nuevo cliente */}
      {showCreate && (
        <div className="rounded-lg border border-dashed border-border bg-white p-4 space-y-3">
          <p className="text-sm text-muted-foreground">
            No se encontró ningún cliente con ese dato. Podés registrarlo ahora:
          </p>
          <form onSubmit={handleCreate} className="space-y-3">
            <input
              type="text"
              value={phone}
              readOnly
              className={inputCls + " bg-secondary text-muted-foreground"}
            />
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Nombre (opcional)"
              className={inputCls}
            />
            <input
              type="text"
              value={newAddress}
              onChange={(e) => setNewAddress(e.target.value)}
              placeholder="Dirección (opcional)"
              className={inputCls}
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className={btnOutline}
              >
                Cancelar
              </button>
              <button type="submit" disabled={creating} className={btnPrimary}>
                {creating ? "Guardando…" : "Registrar cliente"}
              </button>
            </div>
          </form>
        </div>
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
