"use client";

import { useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { isAuthenticated, hasPizzeriaSelected, clearAuth } from "@/lib/auth";

export default function DashboardPage() {
  const router = useRouter();
  const params = useParams();
  const pizzeriaId = params.pizzeria_id as string;

  useEffect(() => {
    if (!isAuthenticated() || !hasPizzeriaSelected()) {
      clearAuth();
      router.replace("/login");
    }
  }, [router]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-secondary/30">
      <div className="rounded-lg border border-border bg-white p-8 shadow-sm text-center space-y-3">
        <h1 className="text-xl font-bold">🍕 Panel — Pizzería #{pizzeriaId}</h1>
        <p className="text-sm text-muted-foreground">
          Panel operativo — próximamente (Fase 10+)
        </p>
        <button
          onClick={() => { clearAuth(); router.push("/login"); }}
          className="mt-2 text-sm text-muted-foreground hover:underline"
        >
          Cerrar sesión
        </button>
      </div>
    </main>
  );
}
