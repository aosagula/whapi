"use client"

/**
 * Página de gestión de números de WhatsApp del comercio.
 * Solo accesible para owner y admin.
 */

import { useEffect, useState, useCallback } from "react"
import { useParams } from "next/navigation"
import { Smartphone, Plus, RefreshCw, Pencil, Trash2, X, Check, RotateCcw } from "lucide-react"
import { api, type WhatsappNumberResponse, type WhatsappStatus } from "@/lib/api"

// ── Helpers ──────────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: WhatsappStatus }) {
  const config: Record<WhatsappStatus, { dot: string; label: string; text: string }> = {
    connected:    { dot: "bg-green-500",  label: "Conectado",     text: "text-green-700" },
    scanning:     { dot: "bg-yellow-400", label: "Esperando QR",  text: "text-yellow-700" },
    disconnected: { dot: "bg-red-400",    label: "Desconectado",  text: "text-red-700" },
  }
  const { dot, label, text } = config[status] ?? config.disconnected
  return (
    <span className={`inline-flex items-center gap-1.5 text-sm font-medium ${text}`}>
      <span className={`w-2 h-2 rounded-full ${dot}`} />
      {label}
    </span>
  )
}

// ── Modal QR ─────────────────────────────────────────────────────────────────

interface ModalQRProps {
  comercioId: string
  numero: WhatsappNumberResponse
  onClose: () => void
  onConnected: () => void
}

function ModalQR({ comercioId, numero, onClose, onConnected }: ModalQRProps) {
  const [qr, setQr] = useState<string | null>(null)
  const [status, setStatus] = useState<WhatsappStatus>(numero.status)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchQR = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await api.whatsapp.obtenerQR(comercioId, numero.id)
      setQr(resp.qr_code)
      setStatus(resp.status)
      if (resp.status === "connected") onConnected()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error al obtener QR")
    } finally {
      setLoading(false)
    }
  }, [comercioId, numero.id, onConnected])

  // Polling cada 5 segundos mientras está en scanning
  useEffect(() => {
    fetchQR()
    const interval = setInterval(() => {
      if (status !== "connected") fetchQR()
    }, 5000)
    return () => clearInterval(interval)
  }, [fetchQR, status])

  return (
    <>
      <div className="fixed inset-0 bg-black/40 z-40" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-brown text-lg">Escanear QR</h2>
            <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 text-gray-400">
              <X className="w-5 h-5" />
            </button>
          </div>

          <p className="text-sm text-gray-500 mb-4">
            Abrí WhatsApp en el teléfono del número <strong>{numero.phone_number}</strong> y
            escaneá este código desde <em>Dispositivos vinculados</em>.
          </p>

          {status === "connected" ? (
            <div className="flex flex-col items-center gap-3 py-6">
              <div className="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center">
                <Check className="w-7 h-7 text-green-600" />
              </div>
              <p className="text-green-700 font-medium">¡Número conectado!</p>
              <button onClick={onClose} className="btn-primary mt-2">Cerrar</button>
            </div>
          ) : loading && !qr ? (
            <div className="flex items-center justify-center py-12 text-gray-400">
              Cargando QR...
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          ) : qr ? (
            <div className="flex flex-col items-center gap-3">
              {/* QR en base64 */}
              <img
                src={qr.startsWith("data:") ? qr : `data:image/png;base64,${qr}`}
                alt="QR de WhatsApp"
                className="w-56 h-56 rounded-xl border border-border"
              />
              <p className="text-xs text-gray-400">Actualizando automáticamente…</p>
            </div>
          ) : (
            <div className="text-center text-sm text-gray-400 py-8">
              No se pudo obtener el QR. Intentá reconectar.
            </div>
          )}
        </div>
      </div>
    </>
  )
}

// ── Modal Agregar ─────────────────────────────────────────────────────────────

interface ModalAgregarProps {
  comercioId: string
  onClose: () => void
  onAdded: (numero: WhatsappNumberResponse) => void
}

function ModalAgregar({ comercioId, onClose, onAdded }: ModalAgregarProps) {
  const [phone, setPhone] = useState("")
  const [label, setLabel] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!phone.trim()) return
    setLoading(true)
    setError(null)
    try {
      const numero = await api.whatsapp.agregar(comercioId, {
        phone_number: phone.trim(),
        label: label.trim() || undefined,
      })
      onAdded(numero)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al agregar el número")
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/40 z-40" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-brown text-lg">Agregar número</h2>
            <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 text-gray-400">
              <X className="w-5 h-5" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Número de teléfono <span className="text-red-500">*</span>
              </label>
              <input
                type="tel"
                placeholder="+54911..."
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
                className="w-full border border-border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Etiqueta (opcional)
              </label>
              <input
                type="text"
                placeholder="Ej: Número principal, Zona Norte..."
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                className="w-full border border-border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30"
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-3 py-2 text-sm text-red-700">
                {error}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={onClose}
                className="btn-outline px-4 py-2 text-sm rounded-xl"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={loading || !phone.trim()}
                className="btn-primary px-4 py-2 text-sm rounded-xl disabled:opacity-50"
              >
                {loading ? "Agregando…" : "Agregar y obtener QR"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function WhatsappPage() {
  const params = useParams<{ comercio_id: string }>()
  const comercioId = params.comercio_id

  const [numeros, setNumeros] = useState<WhatsappNumberResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  // Modal agregar
  const [showAgregar, setShowAgregar] = useState(false)
  // Modal QR: numero seleccionado para ver QR
  const [qrNumero, setQrNumero] = useState<WhatsappNumberResponse | null>(null)
  // Edición inline de etiqueta
  const [editandoId, setEditandoId] = useState<string | null>(null)
  const [editLabel, setEditLabel] = useState("")
  // Eliminación en curso
  const [eliminandoId, setEliminandoId] = useState<string | null>(null)

  const fetchNumeros = useCallback(
    async (showRefresh = false) => {
      if (showRefresh) setRefreshing(true)
      else setLoading(true)
      setError(null)
      try {
        const data = await api.whatsapp.listar(comercioId)
        setNumeros(data)
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Error al cargar números")
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [comercioId],
  )

  useEffect(() => { fetchNumeros() }, [fetchNumeros])

  async function handleGuardarEtiqueta(id: string) {
    try {
      const updated = await api.whatsapp.editar(comercioId, id, { label: editLabel })
      setNumeros((prev) => prev.map((n) => (n.id === id ? updated : n)))
    } finally {
      setEditandoId(null)
    }
  }

  async function handleEliminar(id: string) {
    if (!confirm("¿Eliminar este número? Las conversaciones históricas se conservan.")) return
    setEliminandoId(id)
    try {
      await api.whatsapp.eliminar(comercioId, id)
      setNumeros((prev) => prev.map((n) => (n.id === id ? { ...n, is_active: false, status: "disconnected" } : n)))
    } finally {
      setEliminandoId(null)
    }
  }

  async function handleReconectar(numero: WhatsappNumberResponse) {
    await api.whatsapp.reconectar(comercioId, numero.id)
    setNumeros((prev) => prev.map((n) => (n.id === numero.id ? { ...n, status: "scanning" } : n)))
    setQrNumero({ ...numero, status: "scanning" })
  }

  const desconectados = numeros.filter((n) => n.is_active && n.status === "disconnected")

  return (
    <div className="space-y-6">
      {/* Encabezado */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-serif text-brown">WhatsApp</h1>
          <p className="text-sm text-gray-500 mt-0.5">Números vinculados al comercio</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchNumeros(true)}
            disabled={refreshing}
            className="p-2 border border-border rounded-xl hover:bg-gray-50 transition-colors disabled:opacity-50"
            title="Actualizar"
          >
            <RefreshCw className={`h-4 w-4 text-gray-500 ${refreshing ? "animate-spin" : ""}`} />
          </button>
          <button
            onClick={() => setShowAgregar(true)}
            className="btn-primary flex items-center gap-2 px-4 py-2 text-sm rounded-xl"
          >
            <Plus className="w-4 h-4" />
            Agregar número
          </button>
        </div>
      </div>

      {/* Alerta de números desconectados */}
      {desconectados.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-800 flex items-start gap-2">
          <span className="mt-0.5">⚠️</span>
          <span>
            {desconectados.length === 1
              ? `El número "${desconectados[0].label ?? desconectados[0].phone_number}" está desconectado.`
              : `${desconectados.length} números están desconectados.`}{" "}
            Reconectá para seguir recibiendo mensajes.
          </span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Tabla */}
      {loading ? (
        <div className="text-center py-16 text-gray-400">Cargando números…</div>
      ) : numeros.length === 0 ? (
        <div className="card flex flex-col items-center gap-4 py-16 text-center">
          <Smartphone className="w-10 h-10 text-gray-300" />
          <div>
            <p className="font-medium text-brown">No hay números vinculados</p>
            <p className="text-sm text-gray-500 mt-1">
              Agregá un número para empezar a recibir pedidos por WhatsApp.
            </p>
          </div>
          <button
            onClick={() => setShowAgregar(true)}
            className="btn-primary flex items-center gap-2 px-4 py-2 text-sm rounded-xl mt-2"
          >
            <Plus className="w-4 h-4" />
            Agregar primer número
          </button>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-border">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Número</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Etiqueta</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Estado</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {numeros.map((numero) => (
                <tr
                  key={numero.id}
                  className={`transition-colors ${!numero.is_active ? "opacity-50" : "hover:bg-[#faf7f2]"}`}
                >
                  {/* Número */}
                  <td className="px-4 py-3 font-mono text-brown">{numero.phone_number}</td>

                  {/* Etiqueta (edición inline) */}
                  <td className="px-4 py-3">
                    {editandoId === numero.id ? (
                      <div className="flex items-center gap-1">
                        <input
                          autoFocus
                          value={editLabel}
                          onChange={(e) => setEditLabel(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleGuardarEtiqueta(numero.id)
                            if (e.key === "Escape") setEditandoId(null)
                          }}
                          className="border border-border rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 w-40"
                        />
                        <button
                          onClick={() => handleGuardarEtiqueta(numero.id)}
                          className="p-1 rounded-lg text-green-600 hover:bg-green-50"
                          title="Guardar"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setEditandoId(null)}
                          className="p-1 rounded-lg text-gray-400 hover:bg-gray-100"
                          title="Cancelar"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <span className="text-gray-600">
                        {numero.label ?? <span className="text-gray-400 italic">Sin etiqueta</span>}
                      </span>
                    )}
                  </td>

                  {/* Estado */}
                  <td className="px-4 py-3">
                    {!numero.is_active ? (
                      <span className="text-sm text-gray-400">Eliminado</span>
                    ) : (
                      <StatusBadge status={numero.status} />
                    )}
                  </td>

                  {/* Acciones */}
                  <td className="px-4 py-3">
                    {numero.is_active && (
                      <div className="flex items-center justify-end gap-1">
                        {/* Ver QR (si está en scanning) o reconectar (si está desconectado) */}
                        {numero.status === "scanning" && (
                          <button
                            onClick={() => setQrNumero(numero)}
                            className="p-1.5 rounded-lg hover:bg-brand-pale text-brand transition-colors"
                            title="Ver QR"
                          >
                            <Smartphone className="w-4 h-4" />
                          </button>
                        )}
                        {numero.status === "disconnected" && (
                          <button
                            onClick={() => handleReconectar(numero)}
                            className="p-1.5 rounded-lg hover:bg-amber-50 text-amber-600 transition-colors"
                            title="Reconectar"
                          >
                            <RotateCcw className="w-4 h-4" />
                          </button>
                        )}

                        {/* Editar etiqueta */}
                        <button
                          onClick={() => {
                            setEditandoId(numero.id)
                            setEditLabel(numero.label ?? "")
                          }}
                          className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
                          title="Editar etiqueta"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>

                        {/* Eliminar */}
                        <button
                          onClick={() => handleEliminar(numero.id)}
                          disabled={eliminandoId === numero.id}
                          className="p-1.5 rounded-lg hover:bg-red-50 text-red-400 transition-colors disabled:opacity-40"
                          title="Eliminar"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal: agregar número */}
      {showAgregar && (
        <ModalAgregar
          comercioId={comercioId}
          onClose={() => setShowAgregar(false)}
          onAdded={(numero) => {
            setNumeros((prev) => [...prev, numero])
            setShowAgregar(false)
            setQrNumero(numero)
          }}
        />
      )}

      {/* Modal: ver QR */}
      {qrNumero && (
        <ModalQR
          comercioId={comercioId}
          numero={qrNumero}
          onClose={() => setQrNumero(null)}
          onConnected={() => {
            fetchNumeros(true)
            setQrNumero(null)
          }}
        />
      )}
    </div>
  )
}
