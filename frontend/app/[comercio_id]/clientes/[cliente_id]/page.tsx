"use client"

/**
 * Detalle de un cliente: datos, saldo de crédito, historial de movimientos y pedidos.
 */
import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft, Pencil, Check, X, Plus, Minus } from "lucide-react"
import {
  api,
  ApiError,
  ClienteResponse,
  CreditoResponse,
  PedidoResumenResponse,
} from "@/lib/api"

// ── Labels ──────────────────────────────────────────────────────────────────

const ORDER_STATUS_LABEL: Record<string, string> = {
  in_progress: "En curso",
  pending_payment: "Pago pendiente",
  pending_preparation: "Pendiente preparación",
  in_preparation: "En preparación",
  to_dispatch: "Para despachar",
  in_delivery: "En camino",
  delivered: "Entregado",
  cancelled: "Cancelado",
  with_incident: "Con incidencia",
  discarded: "Descartado",
}

const ORIGIN_LABEL: Record<string, string> = {
  whatsapp: "WhatsApp",
  phone: "Telefónico",
  operator: "Operador",
}

// ── Componente principal ─────────────────────────────────────────────────────

export default function DetalleClientePage() {
  const params = useParams()
  const router = useRouter()
  const comercioId = params.comercio_id as string
  const clienteId = params.cliente_id as string

  const userRole =
    typeof window !== "undefined" ? (localStorage.getItem("comercio_role") ?? "cashier") : "cashier"
  const puedeGestionar = userRole === "owner" || userRole === "admin"

  const [cliente, setCliente] = useState<ClienteResponse | null>(null)
  const [creditos, setCreditos] = useState<CreditoResponse[]>([])
  const [pedidos, setPedidos] = useState<PedidoResumenResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Estado de edición inline
  const [editando, setEditando] = useState<"name" | "address" | null>(null)
  const [editValue, setEditValue] = useState("")
  const [guardando, setGuardando] = useState(false)

  // Modal ajuste de crédito
  const [modalCredito, setModalCredito] = useState(false)
  const [creditoAmount, setCreditoAmount] = useState("")
  const [creditoReason, setCreditoReason] = useState("")
  const [creditoError, setCreditoError] = useState<string | null>(null)
  const [creditoLoading, setCreditoLoading] = useState(false)

  useEffect(() => {
    async function cargar() {
      setLoading(true)
      setError(null)
      try {
        const [c, cr, p] = await Promise.all([
          api.clientes.obtener(comercioId, clienteId),
          api.clientes.listarCreditos(comercioId, clienteId),
          api.clientes.listarPedidos(comercioId, clienteId),
        ])
        setCliente(c)
        setCreditos(cr)
        setPedidos(p)
      } catch {
        setError("No se pudo cargar la información del cliente.")
      } finally {
        setLoading(false)
      }
    }
    cargar()
  }, [comercioId, clienteId])

  // ── Edición inline ─────────────────────────────────────────────────────────

  function iniciarEdicion(campo: "name" | "address") {
    setEditando(campo)
    setEditValue(campo === "name" ? (cliente?.name ?? "") : (cliente?.address ?? ""))
  }

  async function guardarEdicion() {
    if (!editando || !cliente) return
    setGuardando(true)
    try {
      const updated = await api.clientes.actualizar(comercioId, clienteId, {
        [editando]: editValue || null,
      })
      setCliente(updated)
      setEditando(null)
    } catch {
      // silencioso: el campo queda como estaba
    } finally {
      setGuardando(false)
    }
  }

  function cancelarEdicion() {
    setEditando(null)
  }

  // ── Ajuste de crédito ──────────────────────────────────────────────────────

  async function confirmarAjusteCredito() {
    const amount = parseFloat(creditoAmount)
    if (isNaN(amount) || amount === 0) {
      setCreditoError("Ingresá un monto válido distinto de cero.")
      return
    }
    setCreditoLoading(true)
    setCreditoError(null)
    try {
      await api.clientes.ajustarCredito(comercioId, clienteId, {
        amount,
        reason: creditoReason || undefined,
      })
      // Recargar cliente y créditos
      const [c, cr] = await Promise.all([
        api.clientes.obtener(comercioId, clienteId),
        api.clientes.listarCreditos(comercioId, clienteId),
      ])
      setCliente(c)
      setCreditos(cr)
      setModalCredito(false)
      setCreditoAmount("")
      setCreditoReason("")
    } catch (err) {
      if (err instanceof ApiError) {
        setCreditoError(err.message)
      } else {
        setCreditoError("No se pudo aplicar el ajuste.")
      }
    } finally {
      setCreditoLoading(false)
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="py-20 flex flex-col items-center gap-3 text-brown-muted">
        <div className="w-6 h-6 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm">Cargando cliente...</span>
      </div>
    )
  }

  if (error || !cliente) {
    return (
      <div className="py-20 text-center">
        <p className="text-red-500 text-sm mb-4">{error ?? "Cliente no encontrado."}</p>
        <button
          onClick={() => router.push(`/${comercioId}/clientes`)}
          className="text-sm text-amber-600 hover:underline"
        >
          Volver al listado
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-3xl">
      {/* Encabezado */}
      <div className="mb-6 flex items-center gap-3">
        <button
          aria-label="Volver al listado"
          onClick={() => router.push(`/${comercioId}/clientes`)}
          className="p-2 rounded-lg hover:bg-stone-100 transition-colors text-brown-muted"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="font-serif text-3xl text-brown">
            {cliente.name ?? <span className="italic text-brown-muted">Sin nombre</span>}
          </h1>
          <p className="text-brown-muted text-sm mt-0.5">{cliente.phone}</p>
        </div>
      </div>

      {/* Datos del cliente */}
      <div className="bg-white border border-stone-200 rounded-2xl shadow-sm p-6 mb-6">
        <h2 className="font-semibold text-brown mb-4 text-sm uppercase tracking-wide">Datos</h2>
        <div className="space-y-4">
          {/* Nombre */}
          <CampoEditable
            label="Nombre"
            valor={cliente.name ?? "—"}
            editando={editando === "name"}
            editValue={editValue}
            guardando={guardando}
            onEditar={() => iniciarEdicion("name")}
            onGuardar={guardarEdicion}
            onCancelar={cancelarEdicion}
            onChange={setEditValue}
          />
          {/* Dirección */}
          <CampoEditable
            label="Dirección"
            valor={cliente.address ?? "—"}
            editando={editando === "address"}
            editValue={editValue}
            guardando={guardando}
            onEditar={() => iniciarEdicion("address")}
            onGuardar={guardarEdicion}
            onCancelar={cancelarEdicion}
            onChange={setEditValue}
          />
          {/* Alta */}
          <div className="flex items-center justify-between py-2 border-b border-stone-100 last:border-0">
            <span className="text-brown-muted text-sm">Alta</span>
            <span className="text-brown text-sm">
              {new Date(cliente.created_at).toLocaleDateString("es-AR", {
                day: "2-digit",
                month: "long",
                year: "numeric",
              })}
            </span>
          </div>
        </div>
      </div>

      {/* Saldo de crédito */}
      <div className="bg-white border border-stone-200 rounded-2xl shadow-sm p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-brown text-sm uppercase tracking-wide">Crédito</h2>
          {puedeGestionar && (
            <button
              onClick={() => { setCreditoError(null); setCreditoAmount(""); setCreditoReason(""); setModalCredito(true) }}
              className="flex items-center gap-1.5 text-xs font-medium text-amber-700 hover:text-amber-900 border border-amber-300 rounded-lg px-3 py-1.5 hover:bg-amber-50 transition-colors"
            >
              <Pencil className="w-3.5 h-3.5" />
              Ajustar
            </button>
          )}
        </div>

        {/* Saldo actual */}
        <div className="flex items-baseline gap-1 mb-4">
          <span className="text-3xl font-bold text-brown">${cliente.credit_balance.toFixed(2)}</span>
          <span className="text-brown-muted text-sm">a favor</span>
        </div>

        {/* Historial de movimientos */}
        {creditos.length === 0 ? (
          <p className="text-brown-muted text-sm">Sin movimientos de crédito.</p>
        ) : (
          <div className="space-y-2">
            {creditos.map((cr) => (
              <div key={cr.id} className="flex items-center justify-between text-sm py-1.5 border-b border-stone-100 last:border-0">
                <div>
                  <span className="text-brown">{cr.reason ?? "Ajuste"}</span>
                  <span className="block text-xs text-brown-muted">
                    {new Date(cr.created_at).toLocaleDateString("es-AR", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })}
                  </span>
                </div>
                <span className={`font-semibold ${cr.amount >= 0 ? "text-green-600" : "text-red-500"}`}>
                  {cr.amount >= 0 ? "+" : ""}${cr.amount.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Historial de pedidos */}
      <div className="bg-white border border-stone-200 rounded-2xl shadow-sm p-6">
        <h2 className="font-semibold text-brown mb-4 text-sm uppercase tracking-wide">
          Pedidos ({pedidos.length})
        </h2>
        {pedidos.length === 0 ? (
          <p className="text-brown-muted text-sm">Sin pedidos registrados.</p>
        ) : (
          <div className="space-y-2">
            {pedidos.map((p) => (
              <div
                key={p.id}
                onClick={() => router.push(`/${comercioId}/pedidos?pedido=${p.id}`)}
                className="flex items-center justify-between py-2 border-b border-stone-100 last:border-0 hover:bg-stone-50 cursor-pointer rounded px-2 -mx-2 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-brown-muted text-xs font-mono">#{p.order_number}</span>
                  <div>
                    <span className="text-brown text-sm">{ORDER_STATUS_LABEL[p.status] ?? p.status}</span>
                    <span className="block text-xs text-brown-muted">
                      {ORIGIN_LABEL[p.origin] ?? p.origin} ·{" "}
                      {new Date(p.created_at).toLocaleDateString("es-AR", {
                        day: "2-digit",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                  </div>
                </div>
                <span className="text-brown font-medium text-sm">${p.total_amount.toFixed(2)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal ajuste de crédito */}
      {modalCredito && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <h3 className="font-semibold text-brown text-lg mb-4">Ajustar crédito</h3>

            <div className="mb-4">
              <label className="block text-sm text-brown-muted mb-1">
                Monto (positivo = acreditar, negativo = descontar)
              </label>
              <div className="flex gap-2">
                <button
                  onClick={() => setCreditoAmount((v) => {
                    const n = parseFloat(v) || 0
                    return n >= 0 ? String(n) : String(-n)
                  })}
                  className="p-2 border border-stone-200 rounded-lg hover:bg-stone-50"
                  title="Acreditar"
                >
                  <Plus className="w-4 h-4 text-green-600" />
                </button>
                <input
                  type="number"
                  step="0.01"
                  value={creditoAmount}
                  onChange={(e) => setCreditoAmount(e.target.value)}
                  placeholder="0.00"
                  className="flex-1 border border-stone-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                />
                <button
                  onClick={() => setCreditoAmount((v) => {
                    const n = parseFloat(v) || 0
                    return n <= 0 ? String(n) : String(-n)
                  })}
                  className="p-2 border border-stone-200 rounded-lg hover:bg-stone-50"
                  title="Descontar"
                >
                  <Minus className="w-4 h-4 text-red-500" />
                </button>
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm text-brown-muted mb-1">Motivo (opcional)</label>
              <input
                type="text"
                value={creditoReason}
                onChange={(e) => setCreditoReason(e.target.value)}
                placeholder="Ej: Ajuste por cancelación manual"
                className="w-full border border-stone-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
              />
            </div>

            {creditoError && (
              <p className="text-red-500 text-xs mb-3">{creditoError}</p>
            )}

            <div className="flex gap-2">
              <button
                onClick={() => setModalCredito(false)}
                className="flex-1 py-2 border border-stone-200 rounded-lg text-sm text-brown-muted hover:bg-stone-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={confirmarAjusteCredito}
                disabled={creditoLoading}
                className="flex-1 py-2 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600 disabled:opacity-50 transition-colors"
              >
                {creditoLoading ? "Guardando..." : "Confirmar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Subcomponente campo editable ─────────────────────────────────────────────

interface CampoEditableProps {
  label: string
  valor: string
  editando: boolean
  editValue: string
  guardando: boolean
  onEditar: () => void
  onGuardar: () => void
  onCancelar: () => void
  onChange: (v: string) => void
}

function CampoEditable({
  label,
  valor,
  editando,
  editValue,
  guardando,
  onEditar,
  onGuardar,
  onCancelar,
  onChange,
}: CampoEditableProps) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-stone-100 last:border-0">
      <span className="text-brown-muted text-sm w-24 shrink-0">{label}</span>
      {editando ? (
        <div className="flex items-center gap-2 flex-1">
          <input
            autoFocus
            type="text"
            value={editValue}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") onGuardar(); if (e.key === "Escape") onCancelar() }}
            className="flex-1 border border-stone-200 rounded-lg px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
          <button
            onClick={onGuardar}
            disabled={guardando}
            className="p-1.5 rounded-lg bg-amber-500 text-white hover:bg-amber-600 disabled:opacity-50"
          >
            <Check className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onCancelar}
            className="p-1.5 rounded-lg border border-stone-200 text-brown-muted hover:bg-stone-50"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2 flex-1 justify-end">
          <span className="text-brown text-sm text-right">{valor}</span>
          <button
            onClick={onEditar}
            className="p-1 rounded hover:bg-stone-100 text-brown-muted opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <Pencil className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  )
}
