"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api";
import { ChatSessionDetail, ChatSessionStatus } from "@/lib/types";
import ChatView from "@/components/conversaciones/ChatView";

const POLL_MS = 10_000;

const STATUS_TABS: { id: ChatSessionStatus | "all"; label: string }[] = [
  { id: "all", label: "Todas" },
  { id: "waiting_human", label: "⏳ Esperando" },
  { id: "transferred_human", label: "👤 En curso" },
  { id: "active", label: "🤖 Bot" },
];

const STATUS_COLOR: Record<ChatSessionStatus, string> = {
  active: "bg-blue-100 text-blue-700",
  waiting_human: "bg-yellow-100 text-yellow-700",
  transferred_human: "bg-green-100 text-green-700",
  closed: "bg-secondary text-muted-foreground",
};

export default function ConversacionesPage() {
  const { pizzeria_id } = useParams<{ pizzeria_id: string }>();
  const [sessions, setSessions] = useState<ChatSessionDetail[]>([]);
  const [selected, setSelected] = useState<ChatSessionDetail | null>(null);
  const [tab, setTab] = useState<ChatSessionStatus | "all">("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchSessions = useCallback(async () => {
    try {
      const qs = tab !== "all" ? `?status=${tab}` : "";
      const data = await apiFetch<ChatSessionDetail[]>(
        `/pizzerias/${pizzeria_id}/conversaciones${qs}`
      );
      setSessions(data);
      setError(null);
      // Actualizar sesión seleccionada si está en la lista
      if (selected) {
        const refreshed = data.find((s) => s.id === selected.id);
        if (refreshed) setSelected(refreshed);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar conversaciones");
    } finally {
      setLoading(false);
    }
  }, [pizzeria_id, tab, selected]);

  useEffect(() => {
    setLoading(true);
    fetchSessions();
    timerRef.current = setInterval(fetchSessions, POLL_MS);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [pizzeria_id, tab]);   // eslint-disable-line react-hooks/exhaustive-deps

  function handleUpdate(updated: ChatSessionDetail) {
    setSessions((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
    setSelected(updated);
  }

  return (
    <div className="flex h-[calc(100vh-57px)]">
      {/* Panel izquierdo — lista */}
      <aside className="flex w-72 flex-shrink-0 flex-col border-r border-border bg-white">
        {/* Tabs de filtro */}
        <div className="border-b border-border p-2 flex flex-wrap gap-1">
          {STATUS_TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => { setTab(t.id); setSelected(null); }}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                tab === t.id
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-secondary"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Lista */}
        <div className="flex-1 overflow-y-auto">
          {loading && (
            <p className="py-8 text-center text-sm text-muted-foreground">Cargando…</p>
          )}
          {error && (
            <p className="p-4 text-sm text-destructive">{error}</p>
          )}
          {!loading && sessions.length === 0 && (
            <p className="py-8 text-center text-sm text-muted-foreground">
              Sin conversaciones.
            </p>
          )}
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => setSelected(session)}
              className={`w-full border-b border-border px-4 py-3 text-left transition-colors hover:bg-secondary/50 ${
                selected?.id === session.id ? "bg-secondary" : ""
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-sm">
                    {session.customer_name ?? session.customer_phone}
                  </p>
                  {session.customer_name && (
                    <p className="text-xs text-muted-foreground truncate">
                      {session.customer_phone}
                    </p>
                  )}
                </div>
                <span className={`flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[session.status]}`}>
                  {session.status === "active" ? "Bot"
                    : session.status === "waiting_human" ? "Espera"
                    : session.status === "transferred_human" ? "HITL"
                    : "Cerrada"}
                </span>
              </div>
              {session.messages.length > 0 && (
                <p className="mt-1 truncate text-xs text-muted-foreground">
                  {session.messages[session.messages.length - 1].content}
                </p>
              )}
              <p className="mt-0.5 text-xs text-muted-foreground/70">
                {new Date(session.updated_at).toLocaleString("es-AR", {
                  day: "2-digit", month: "2-digit",
                  hour: "2-digit", minute: "2-digit",
                })}
              </p>
            </button>
          ))}
        </div>
      </aside>

      {/* Panel derecho — chat */}
      <main className="flex flex-1 flex-col">
        {selected ? (
          <ChatView
            session={selected}
            pizzeriaId={pizzeria_id}
            onUpdate={handleUpdate}
          />
        ) : (
          <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
            Seleccioná una conversación
          </div>
        )}
      </main>
    </div>
  );
}
