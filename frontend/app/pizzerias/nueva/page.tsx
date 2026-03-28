"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";

interface PizzeriaRead {
  id: number;
  name: string;
}

export default function NuevaPizzeriaPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) router.replace("/login");
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await apiFetch<PizzeriaRead>("/pizzerias", {
        method: "POST",
        body: JSON.stringify({
          name,
          address: address || undefined,
          city: city || undefined,
        }),
      });
      router.push("/selector");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error inesperado");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-secondary/30">
      <div className="w-full max-w-sm space-y-6 rounded-lg border border-border bg-white p-8 shadow-sm">
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-bold tracking-tight">🍕 Nueva pizzería</h1>
          <p className="text-sm text-muted-foreground">
            Completá los datos para crear tu primera pizzería
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Field label="Nombre *" htmlFor="name">
            <input
              id="name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="La Napolitana"
              className={inputCls}
            />
          </Field>

          <Field label="Dirección" htmlFor="address">
            <input
              id="address"
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Av. Corrientes 1234"
              className={inputCls}
            />
          </Field>

          <Field label="Ciudad" htmlFor="city">
            <input
              id="city"
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="Buenos Aires"
              className={inputCls}
            />
          </Field>

          {error && (
            <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60 transition-opacity"
          >
            {loading ? "Creando…" : "Crear pizzería"}
          </button>
        </form>

        <button
          onClick={() => router.push("/selector")}
          className="w-full text-center text-sm text-muted-foreground hover:underline"
        >
          Cancelar
        </button>
      </div>
    </main>
  );
}

const inputCls =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring";

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label htmlFor={htmlFor} className="text-sm font-medium">
        {label}
      </label>
      {children}
    </div>
  );
}
