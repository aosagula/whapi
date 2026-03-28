"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api";
import { getToken, setToken, setPizzeriaId, setRole, clearAuth } from "@/lib/auth";

interface PizzeriaItem {
  id: number;
  name: string;
  address: string | null;
}

interface PizzeriaSelectorResponse {
  pizzerias: PizzeriaItem[];
}

interface TokenResponse {
  access_token: string;
  pizzeria_id: number;
  role: string;
}

export default function SelectorPage() {
  const router = useRouter();
  const [pizzerias, setPizzerias] = useState<PizzeriaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selecting, setSelecting] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }

    apiFetch<PizzeriaSelectorResponse>("/auth/pizzerias")
      .then((data) => setPizzerias(data.pizzerias))
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          clearAuth();
          router.replace("/login");
        } else {
          setError(err instanceof ApiError ? err.message : "Error al cargar pizzerías");
        }
      })
      .finally(() => setLoading(false));
  }, [router]);

  async function handleSelect(pizzeriaId: number) {
    setSelecting(pizzeriaId);
    setError(null);
    try {
      const data = await apiFetch<TokenResponse>(
        `/auth/select-pizzeria/${pizzeriaId}`,
        { method: "POST" }
      );
      setToken(data.access_token);
      setPizzeriaId(data.pizzeria_id);
      setRole(data.role);
      router.push(`/${data.pizzeria_id}/dashboard`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al seleccionar pizzería");
      setSelecting(null);
    }
  }

  function handleLogout() {
    clearAuth();
    router.push("/login");
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-secondary/30 px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">🍕 Seleccioná una pizzería</h1>
          <p className="text-sm text-muted-foreground">
            Elegí con cuál trabajar en esta sesión
          </p>
        </div>

        {loading && (
          <div className="text-center py-8 text-sm text-muted-foreground">
            Cargando pizzerías…
          </div>
        )}

        {error && (
          <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive text-center">
            {error}
          </p>
        )}

        {!loading && pizzerias.length === 0 && !error && (
          <div className="rounded-lg border border-border bg-white p-6 text-center space-y-3">
            <p className="text-sm text-muted-foreground">
              No tenés pizzerías creadas todavía.
            </p>
            <a
              href="/pizzerias/nueva"
              className="inline-block rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Crear primera pizzería
            </a>
          </div>
        )}

        {pizzerias.length > 0 && (
          <ul className="space-y-3">
            {pizzerias.map((p) => (
              <li key={p.id}>
                <button
                  onClick={() => handleSelect(p.id)}
                  disabled={selecting !== null}
                  className="w-full rounded-lg border border-border bg-white px-5 py-4 text-left shadow-sm hover:border-primary hover:shadow-md transition-all disabled:opacity-60 group"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium group-hover:text-primary transition-colors">
                        {p.name}
                      </p>
                      {p.address && (
                        <p className="text-sm text-muted-foreground mt-0.5">
                          {p.address}
                        </p>
                      )}
                    </div>
                    <span className="text-muted-foreground group-hover:text-primary transition-colors">
                      {selecting === p.id ? "→…" : "→"}
                    </span>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="text-center">
          <button
            onClick={handleLogout}
            className="text-sm text-muted-foreground hover:text-foreground hover:underline"
          >
            Cerrar sesión
          </button>
        </div>
      </div>
    </main>
  );
}
