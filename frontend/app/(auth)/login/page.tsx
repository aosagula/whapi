"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch, ApiError } from "@/lib/api";
import { setToken, setPizzeriaId, setRole } from "@/lib/auth";

interface TokenResponse {
  access_token: string;
  pizzeria_id?: number;
  role: string;
}

type Tab = "owner" | "employee";

export default function LoginPage() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("owner");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pizzeriaId, setPizzId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (tab === "owner") {
        const data = await apiFetch<TokenResponse>("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
        setToken(data.access_token);
        setRole(data.role);
        router.push("/selector");
      } else {
        const pid = parseInt(pizzeriaId, 10);
        if (isNaN(pid)) {
          setError("El ID de pizzería debe ser un número.");
          return;
        }
        const data = await apiFetch<TokenResponse>("/auth/panel-login", {
          method: "POST",
          body: JSON.stringify({ email, password, pizzeria_id: pid }),
        });
        setToken(data.access_token);
        setRole(data.role);
        if (data.pizzeria_id) {
          setPizzeriaId(data.pizzeria_id);
          router.push(`/${data.pizzeria_id}/dashboard`);
        }
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error inesperado");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-sm space-y-6 rounded-lg border border-border bg-white p-8 shadow-sm">
      <div className="space-y-1 text-center">
        <h1 className="text-2xl font-bold tracking-tight">🍕 Pizzería Chatbot</h1>
        <p className="text-sm text-muted-foreground">Iniciá sesión para continuar</p>
      </div>

      {/* Tabs */}
      <div className="flex rounded-md border border-border overflow-hidden text-sm font-medium">
        <button
          type="button"
          onClick={() => { setTab("owner"); setError(null); }}
          className={`flex-1 py-2 transition-colors ${
            tab === "owner"
              ? "bg-primary text-primary-foreground"
              : "bg-white text-foreground hover:bg-secondary"
          }`}
        >
          Dueño
        </button>
        <button
          type="button"
          onClick={() => { setTab("employee"); setError(null); }}
          className={`flex-1 py-2 transition-colors ${
            tab === "employee"
              ? "bg-primary text-primary-foreground"
              : "bg-white text-foreground hover:bg-secondary"
          }`}
        >
          Empleado
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Email" htmlFor="email">
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="usuario@ejemplo.com"
            className={inputCls}
          />
        </Field>

        <Field label="Contraseña" htmlFor="password">
          <input
            id="password"
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className={inputCls}
          />
        </Field>

        {tab === "employee" && (
          <Field label="ID de pizzería" htmlFor="pizzeria-id">
            <input
              id="pizzeria-id"
              type="number"
              required
              value={pizzeriaId}
              onChange={(e) => setPizzId(e.target.value)}
              placeholder="1"
              className={inputCls}
            />
          </Field>
        )}

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
          {loading ? "Ingresando…" : "Ingresar"}
        </button>
      </form>

      {tab === "owner" && (
        <p className="text-center text-sm text-muted-foreground">
          ¿No tenés cuenta?{" "}
          <Link href="/register" className="text-primary hover:underline">
            Registrate
          </Link>
        </p>
      )}
    </div>
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
