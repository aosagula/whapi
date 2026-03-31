"use client"

/**
 * Lista de conversaciones activas derivadas a humano (HITL).
 * Muestra sesiones en waiting_operator y assigned_human.
 */
import { useEffect, useState, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { MessageSquare, Clock, RefreshCw } from "lucide-react"
import { api, SesionListItem } from "@/lib/api"

function formatWait(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return s > 0 ? `${m}m ${s}s` : `${m}m`
}

const STATUS_LABEL: Record<string, { label: string; color: string }> = {
  waiting_operator: { label: "Esperando operador", color: "bg-red-100 text-red-700" },
  assigned_human: { label: "En atención", color: "bg-amber-100 text-amber-700" },
}

export default function ConversacionesPage() {
  const params = useParams()
  const router = useRouter()
  const comercioId = params.comercio_id as string

  const [sesiones, setSesiones] = useState<SesionListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)

  const cargar = useCallback(async () => {
    setError(null)
    try {
      const data = await api.conversaciones.listar(comercioId)
      setSesiones(data)
    } catch {
      setError("No se pudo cargar las conversaciones.")
    } finally {
      setLoading(false)
    }
  }, [comercioId])

  useEffect(() => {
    cargar()
  }, [cargar, tick])

  // Actualizar contador de tiempo cada segundo
  useEffect(() => {
    const interval = setInterval(() => setTick((t) => t + 1), 10000)
    return () => clearInterval(interval)
  }, [])

  const esperando = sesiones.filter((s) => s.status === "waiting_operator")
  const enAtencion = sesiones.filter((s) => s.status === "assigned_human")

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-serif text-3xl text-brown">Conversaciones</h1>
          <p className="text-brown-muted text-sm mt-1">
            Derivaciones activas que requieren atención humana
          </p>
        </div>
        <button
          onClick={cargar}
          className="flex items-center gap-1.5 text-sm text-brown-muted border border-stone-200 rounded-lg px-3 py-1.5 hover:bg-stone-50 transition-colors"
          title="Actualizar"
        >
          <RefreshCw className="w-4 h-4" />
          Actualizar
        </button>
      </div>

      {loading ? (
        <div className="py-16 flex flex-col items-center gap-3 text-brown-muted">
          <div className="w-6 h-6 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Cargando conversaciones...</span>
        </div>
      ) : error ? (
        <div className="py-16 text-center text-red-500 text-sm">{error}</div>
      ) : sesiones.length === 0 ? (
        <div className="py-16 flex flex-col items-center gap-3 text-brown-muted">
          <MessageSquare className="w-10 h-10 opacity-30" />
          <p className="text-sm">No hay conversaciones activas en este momento.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Esperando operador */}
          {esperando.length > 0 && (
            <section>
              <div className="flex items-center gap-2 mb-3">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
                <h2 className="font-semibold text-brown text-sm uppercase tracking-wide">
                  Esperando operador ({esperando.length})
                </h2>
              </div>
              <div className="bg-white border border-stone-200 rounded-2xl shadow-sm overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-stone-50 border-b border-stone-200">
                    <tr>
                      <th className="text-left px-4 py-3 text-brown-muted font-medium">Cliente</th>
                      <th className="text-left px-4 py-3 text-brown-muted font-medium">Pedido en curso</th>
                      <th className="text-left px-4 py-3 text-brown-muted font-medium">Espera</th>
                      <th className="px-4 py-3" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-100">
                    {esperando.map((s) => (
                      <SesionRow key={s.id} sesion={s} comercioId={comercioId} onAtender={() => router.push(`/${comercioId}/conversaciones/${s.id}`)} />
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* En atención */}
          {enAtencion.length > 0 && (
            <section>
              <div className="flex items-center gap-2 mb-3">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                <h2 className="font-semibold text-brown text-sm uppercase tracking-wide">
                  En atención ({enAtencion.length})
                </h2>
              </div>
              <div className="bg-white border border-stone-200 rounded-2xl shadow-sm overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-stone-50 border-b border-stone-200">
                    <tr>
                      <th className="text-left px-4 py-3 text-brown-muted font-medium">Cliente</th>
                      <th className="text-left px-4 py-3 text-brown-muted font-medium">Pedido en curso</th>
                      <th className="text-left px-4 py-3 text-brown-muted font-medium">Operador</th>
                      <th className="px-4 py-3" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-100">
                    {enAtencion.map((s) => (
                      <SesionRow key={s.id} sesion={s} comercioId={comercioId} onAtender={() => router.push(`/${comercioId}/conversaciones/${s.id}`)} />
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  )
}

// ── Fila de sesión ────────────────────────────────────────────────────────────

function SesionRow({
  sesion,
  onAtender,
}: {
  sesion: SesionListItem
  comercioId: string
  onAtender: () => void
}) {
  const st = STATUS_LABEL[sesion.status]
  const itemsResumen =
    sesion.pedido_en_curso?.items
      .map((i) => `${i.quantity}x ${i.display_name ?? "Producto"}`)
      .join(", ") ?? null

  return (
    <tr className="hover:bg-amber-50 transition-colors">
      <td className="px-4 py-3">
        <div className="font-medium text-brown">{sesion.customer.name ?? "Sin nombre"}</div>
        <div className="text-xs text-brown-muted">{sesion.customer.phone}</div>
      </td>
      <td className="px-4 py-3">
        {sesion.pedido_en_curso ? (
          <div>
            <div className="text-brown">{itemsResumen}</div>
            <div className="text-xs text-brown-muted">
              Subtotal: ${sesion.pedido_en_curso.total_amount.toFixed(2)}
            </div>
          </div>
        ) : (
          <span className="text-brown-muted italic text-xs">Sin ítems</span>
        )}
      </td>
      <td className="px-4 py-3">
        {sesion.status === "waiting_operator" ? (
          <span className="flex items-center gap-1 text-brown-muted text-xs">
            <Clock className="w-3.5 h-3.5" />
            {formatWait(sesion.wait_seconds)}
          </span>
        ) : (
          <span className="text-brown text-xs">{sesion.assigned_operator_name ?? "—"}</span>
        )}
      </td>
      <td className="px-4 py-3 text-right">
        <button
          onClick={onAtender}
          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-500 text-white hover:bg-amber-600 transition-colors"
          data-testid={`btn-atender-${sesion.id}`}
        >
          {sesion.status === "waiting_operator" ? "Atender" : "Ver"}
        </button>
      </td>
    </tr>
  )
}
