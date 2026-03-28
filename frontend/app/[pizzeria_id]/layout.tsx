"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { isAuthenticated, hasPizzeriaSelected, clearAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

interface PizzeriaRead {
  id: number;
  name: string;
}

export default function PizzeriaLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const params = useParams();
  const pizzeriaId = params.pizzeria_id as string;
  const [pizzeriaName, setPizzeriaName] = useState<string>(`Pizzería #${pizzeriaId}`);

  useEffect(() => {
    if (!isAuthenticated() || !hasPizzeriaSelected()) {
      clearAuth();
      router.replace("/login");
      return;
    }
    apiFetch<PizzeriaRead>(`/pizzerias/${pizzeriaId}`)
      .then((p) => setPizzeriaName(p.name))
      .catch(() => {});
  }, [pizzeriaId, router]);

  function handleLogout() {
    clearAuth();
    router.push("/login");
  }

  return (
    <div className="flex min-h-screen flex-col bg-secondary/30">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b border-border bg-white shadow-sm">
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="text-lg font-bold">🍕</span>
            <span className="font-semibold text-foreground">{pizzeriaName}</span>
          </div>

          <nav className="hidden sm:flex items-center gap-1 text-sm font-medium">
            <NavLink href={`/${pizzeriaId}/dashboard`}>Pedidos</NavLink>
            <NavLink href={`/${pizzeriaId}/pedido-telefonico`}>+ Pedido</NavLink>
            <NavLink href={`/${pizzeriaId}/menu`}>Menú</NavLink>
            <NavLink href={`/${pizzeriaId}/clientes`}>Clientes</NavLink>
            <NavLink href={`/${pizzeriaId}/conversaciones`}>Conversaciones</NavLink>
            <NavLink href={`/${pizzeriaId}/configuracion`}>Configuración</NavLink>
          </nav>

          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/selector")}
              className="hidden sm:block text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Cambiar pizzería
            </button>
            <button
              onClick={handleLogout}
              className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-secondary transition-colors"
            >
              Salir
            </button>
          </div>
        </div>
      </header>

      {/* Contenido */}
      <div className="flex-1">{children}</div>
    </div>
  );
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="rounded-md px-3 py-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
    >
      {children}
    </Link>
  );
}
