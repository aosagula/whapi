"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { ChatSessionDetail, ChatSessionStatus } from "@/lib/types";

const STATUS_LABEL: Record<ChatSessionStatus, string> = {
  active: "🤖 Bot activo",
  waiting_human: "⏳ Esperando operador",
  transferred_human: "👤 Operador activo",
  closed: "✓ Cerrada",
};

const STATUS_COLOR: Record<ChatSessionStatus, string> = {
  active: "bg-blue-100 text-blue-800",
  waiting_human: "bg-yellow-100 text-yellow-800",
  transferred_human: "bg-green-100 text-green-800",
  closed: "bg-secondary text-muted-foreground",
};

const ROLE_STYLE: Record<string, string> = {
  user: "justify-start",
  assistant: "justify-end",
  operator: "justify-end",
};

const BUBBLE_STYLE: Record<string, string> = {
  user: "bg-secondary text-foreground",
  assistant: "bg-primary text-primary-foreground",
  operator: "bg-green-600 text-white",
};

const ROLE_LABEL: Record<string, string> = {
  user: "Cliente",
  assistant: "Bot",
  operator: "Operador",
};

interface Props {
  session: ChatSessionDetail;
  pizzeriaId: string;
  onUpdate: (updated: ChatSessionDetail) => void;
}

export default function ChatView({ session, pizzeriaId, onUpdate }: Props) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [transitioning, setTransitioning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session.messages]);

  async function handleStatusChange(newStatus: ChatSessionStatus) {
    setTransitioning(true);
    setError(null);
    try {
      const updated = await apiFetch<ChatSessionDetail>(
        `/pizzerias/${pizzeriaId}/conversaciones/${session.id}/estado`,
        { method: "PATCH", body: JSON.stringify({ status: newStatus }) }
      );
      onUpdate(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cambiar estado");
    } finally {
      setTransitioning(false);
    }
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setSending(true);
    setError(null);
    try {
      const updated = await apiFetch<ChatSessionDetail>(
        `/pizzerias/${pizzeriaId}/conversaciones/${session.id}/mensajes`,
        { method: "POST", body: JSON.stringify({ text: text.trim() }) }
      );
      setText("");
      onUpdate(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al enviar mensaje");
    } finally {
      setSending(false);
    }
  }

  const isHITL = session.status === "transferred_human";

  return (
    <div className="flex flex-col h-full">
      {/* Header de la sesión */}
      <div className="flex items-center justify-between border-b border-border bg-white px-4 py-3">
        <div>
          <p className="font-semibold">
            {session.customer_name ?? session.customer_phone}
          </p>
          <p className="text-xs text-muted-foreground">
            {session.customer_name ? session.customer_phone : ""}{" "}
            · sesión #{session.id}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_COLOR[session.status]}`}>
            {STATUS_LABEL[session.status]}
          </span>
          {/* Acciones HITL */}
          {session.status === "active" || session.status === "waiting_human" ? (
            <button
              onClick={() => handleStatusChange("transferred_human")}
              disabled={transitioning}
              className="rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-60 transition-colors"
            >
              Tomar conversación
            </button>
          ) : null}
          {session.status === "transferred_human" ? (
            <button
              onClick={() => handleStatusChange("active")}
              disabled={transitioning}
              className="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-secondary disabled:opacity-60 transition-colors"
            >
              Devolver al bot
            </button>
          ) : null}
          {session.status !== "closed" && (
            <button
              onClick={() => handleStatusChange("closed")}
              disabled={transitioning}
              className="rounded-md border border-destructive/40 px-3 py-1.5 text-xs text-destructive hover:bg-destructive/10 disabled:opacity-60 transition-colors"
            >
              Cerrar
            </button>
          )}
        </div>
      </div>

      {/* Mensajes */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {session.messages.length === 0 && (
          <p className="text-center text-sm text-muted-foreground py-8">
            Sin mensajes aún.
          </p>
        )}
        {session.messages.map((msg, idx) => (
          <div key={idx} className={`flex ${ROLE_STYLE[msg.role] ?? "justify-start"}`}>
            <div className="max-w-[75%] space-y-1">
              <p className="text-xs text-muted-foreground px-1">
                {ROLE_LABEL[msg.role] ?? msg.role}
              </p>
              <div className={`rounded-2xl px-3 py-2 text-sm ${BUBBLE_STYLE[msg.role] ?? "bg-secondary"}`}>
                {msg.content}
              </div>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Error */}
      {error && (
        <p className="mx-4 mb-2 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}

      {/* Input de mensaje (solo en HITL) */}
      {isHITL ? (
        <form
          onSubmit={handleSend}
          className="flex gap-2 border-t border-border bg-white px-4 py-3"
        >
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Escribí un mensaje…"
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            autoFocus
          />
          <button
            type="submit"
            disabled={sending || !text.trim()}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60 transition-colors"
          >
            {sending ? "…" : "Enviar"}
          </button>
        </form>
      ) : (
        <div className="border-t border-border bg-secondary/30 px-4 py-3 text-center text-xs text-muted-foreground">
          {session.status === "closed"
            ? "Sesión cerrada."
            : "Tomá la conversación para enviar mensajes manuales."}
        </div>
      )}
    </div>
  );
}
