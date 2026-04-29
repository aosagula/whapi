"use client"

/**
 * Lista de chats de WhatsApp del comercio.
 * Muestra nombre, teléfono y estado actual de cada conversación.
 */
import { useEffect, useState, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { MessageSquare, RefreshCw } from "lucide-react"
import { api, SesionListItem } from "@/lib/api"

const STATUS_LABEL: Record<string, { label: string; className: string }> = {
  active_bot: { label: "Bot activo", className: "bg-blue-100 text-blue-700" },
  waiting_operator: { label: "Esperando operador", className: "bg-red-100 text-red-700" },
  assigned_human: { label: "En atención", className: "bg-amber-100 text-amber-700" },
  closed: { label: "Finalizada", className: "bg-stone-100 text-stone-700" },
}

function formatDate(value: string | null): string {
  if (!value) return "Sin mensajes"
  return new Date(value).toLocaleString("es-AR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export default function ConversacionesPage() {
  const params = useParams()
  const router = useRouter()
  const comercioId = params.comercio_id as string

  const [sesiones, setSesiones] = useState<SesionListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const cargar = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    else setLoading(true)
    setError(null)
    try {
      const data = await api.conversaciones.listar(comercioId)
      setSesiones(data)
    } catch {
      setError("No se pudo cargar las conversaciones.")
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [comercioId])

  useEffect(() => {
    cargar()
  }, [cargar])

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-serif text-3xl text-brown">Conversaciones</h1>
          <p className="text-brown-muted text-sm mt-1">
            Chats de WhatsApp del comercio con su estado actual.
          </p>
        </div>
        <button
          onClick={() => cargar(true)}
          disabled={refreshing}
          className="flex items-center gap-1.5 text-sm text-brown-muted border border-stone-200 rounded-lg px-3 py-1.5 hover:bg-stone-50 transition-colors disabled:opacity-50"
          title="Actualizar"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
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
          <p className="text-sm">No hay chats de WhatsApp registrados todavía.</p>
        </div>
      ) : (
        <div className="bg-white border border-stone-200 rounded-2xl shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-stone-50 border-b border-stone-200">
              <tr>
                <th className="text-left px-4 py-3 text-brown-muted font-medium">Cliente</th>
                <th className="text-left px-4 py-3 text-brown-muted font-medium">Teléfono</th>
                <th className="text-left px-4 py-3 text-brown-muted font-medium">Estado</th>
                <th className="text-left px-4 py-3 text-brown-muted font-medium">Último mensaje</th>
                <th className="text-left px-4 py-3 text-brown-muted font-medium">Operador</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {sesiones.map((sesion) => (
                <SesionRow
                  key={sesion.id}
                  sesion={sesion}
                  onOpen={() => router.push(`/${comercioId}/conversaciones/${sesion.id}`)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function SesionRow({
  sesion,
  onOpen,
}: {
  sesion: SesionListItem
  onOpen: () => void
}) {
  const status = STATUS_LABEL[sesion.status] ?? STATUS_LABEL.closed

  return (
    <tr className="hover:bg-amber-50 transition-colors">
      <td className="px-4 py-3">
        <div className="font-medium text-brown">{sesion.customer.name ?? "Sin nombre"}</div>
      </td>
      <td className="px-4 py-3 text-brown-muted">{sesion.customer.phone}</td>
      <td className="px-4 py-3">
        <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${status.className}`}>
          {status.label}
        </span>
      </td>
      <td className="px-4 py-3 text-brown-muted">{formatDate(sesion.last_message_at)}</td>
      <td className="px-4 py-3 text-brown-muted">{sesion.assigned_operator_name ?? "—"}</td>
      <td className="px-4 py-3 text-right">
        <button
          onClick={onOpen}
          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-500 text-white hover:bg-amber-600 transition-colors"
          data-testid={`btn-ver-${sesion.id}`}
        >
          Ver chat
        </button>
      </td>
    </tr>
  )
}
