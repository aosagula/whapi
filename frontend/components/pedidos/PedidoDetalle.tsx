"use client"

/**
 * Panel lateral de detalle de un pedido: items, historial, notas, acciones.
 */

import { useState } from "react"
import { X, ChevronRight, AlertTriangle, Link2, Copy, Check } from "lucide-react"
import { api, type OrderResponse } from "@/lib/api"
import {
  ORDER_STATUS_LABELS,
  ORDER_STATUS_COLORS,
  PAYMENT_STATUS_LABELS,
  PAYMENT_STATUS_COLORS,
  DELIVERY_TYPE_LABELS,
  ORIGIN_LABELS,
  NEXT_STATUS,
  NEXT_STATUS_BUTTON_LABELS,
  INCIDENT_TYPE_LABELS,
  formatCurrency,
  formatDateTime,
} from "./order-utils"
import CancelarModal from "./CancelarModal"
import IncidenciaModal from "./IncidenciaModal"

interface Props {
  pedido: OrderResponse
  comercioId: string
  userRole: string
  onClose: () => void
  onUpdated: (updated: OrderResponse) => void
}

export default function PedidoDetalle({ pedido, comercioId, userRole, onClose, onUpdated }: Props) {
  const [savingNotes, setSavingNotes] = useState(false)
  const [notes, setNotes] = useState(pedido.internal_notes ?? "")
  const [advancing, setAdvancing] = useState(false)
  const [showCancel, setShowCancel] = useState(false)
  const [showIncidencia, setShowIncidencia] = useState(false)
  const [generandoLink, setGenerandoLink] = useState(false)
  const [pagoLink, setPagoLink] = useState<string | null>(null)
  const [linkCopiado, setLinkCopiado] = useState(false)

  const canCancel = ["cashier", "admin", "owner"].includes(userRole) && pedido.status !== "delivered"
  const canMarkPaid = ["cashier", "admin", "owner"].includes(userRole)
  const canGeneratePayLink = ["owner", "admin"].includes(userRole) && pedido.payment_status === "pending_payment"
  const canReportIncident = ["cashier", "admin", "owner", "delivery"].includes(userRole)
  const nextStatus = NEXT_STATUS[pedido.status]

  function advanceAllowed(): boolean {
    if (!nextStatus) return false
    if (userRole === "cook") return ["pending_preparation", "in_preparation"].includes(pedido.status)
    if (userRole === "delivery") return ["to_dispatch", "in_delivery"].includes(pedido.status)
    return ["cashier", "admin", "owner"].includes(userRole)
  }

  async function handleAdvance() {
    if (!nextStatus) return
    setAdvancing(true)
    try {
      const updated = await api.pedidos.cambiarEstado(comercioId, pedido.id, nextStatus)
      onUpdated(updated)
    } finally {
      setAdvancing(false)
    }
  }

  async function handleSaveNotes() {
    setSavingNotes(true)
    try {
      const updated = await api.pedidos.actualizarNotas(comercioId, pedido.id, notes || null)
      onUpdated(updated)
    } finally {
      setSavingNotes(false)
    }
  }

  async function handleMarkPaid() {
    const updated = await api.pedidos.marcarPago(comercioId, pedido.id, "paid")
    onUpdated(updated)
  }

  async function handleGenerarLink() {
    setGenerandoLink(true)
    try {
      const resp = await api.pagos.generarLink(comercioId, pedido.id)
      setPagoLink(resp.init_point)
    } finally {
      setGenerandoLink(false)
    }
  }

  async function handleCopiarLink() {
    if (!pagoLink) return
    await navigator.clipboard.writeText(pagoLink)
    setLinkCopiado(true)
    setTimeout(() => setLinkCopiado(false), 2000)
  }

  async function handleResolveRedispatch(incidentId: string) {
    const updated = await api.pedidos.resolverRedespacho(comercioId, pedido.id, incidentId)
    onUpdated(updated)
  }

  const statusColor = ORDER_STATUS_COLORS[pedido.status] ?? "bg-gray-100 text-gray-600"
  const paymentColor = PAYMENT_STATUS_COLORS[pedido.payment_status] ?? "bg-gray-100 text-gray-500"

  return (
    <>
      {/* Overlay */}
      <div className="fixed inset-0 bg-black/40 z-40" onClick={onClose} />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-full max-w-lg bg-white z-50 shadow-xl flex flex-col overflow-hidden">
        {/* Encabezado */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold text-brown">Pedido #{pedido.order_number}</span>
            <span className="text-sm text-gray-400">{ORIGIN_LABELS[pedido.origin] ?? pedido.origin}</span>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Contenido scrolleable */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Cliente y entrega */}
          <section>
            <div className="flex flex-wrap items-center gap-1.5 mb-1">
              <span className="font-medium text-brown">{pedido.customer.name ?? "Sin nombre"}</span>
              <span className="text-gray-400">·</span>
              <span className="text-gray-500 text-sm">{pedido.customer.phone}</span>
            </div>
            <div className="text-sm text-gray-600">
              {DELIVERY_TYPE_LABELS[pedido.delivery_type] ?? pedido.delivery_type}
              {pedido.delivery_address && (
                <span className="ml-1 text-gray-400">— {pedido.delivery_address}</span>
              )}
            </div>
            <div className="text-xs text-gray-400 mt-1">
              Recibido: {formatDateTime(pedido.created_at)}
            </div>
          </section>

          {/* Badges de estado */}
          <section className="flex gap-2 flex-wrap">
            <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${statusColor}`}>
              {ORDER_STATUS_LABELS[pedido.status] ?? pedido.status}
            </span>
            <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${paymentColor}`}>
              {PAYMENT_STATUS_LABELS[pedido.payment_status] ?? pedido.payment_status}
            </span>
          </section>

          {/* Productos */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Productos</h3>
            {pedido.items.length === 0 ? (
              <p className="text-sm text-gray-400">Sin items registrados</p>
            ) : (
              <ul className="divide-y divide-gray-100">
                {pedido.items.map((item) => (
                  <li key={item.id} className="py-1.5 flex justify-between text-sm">
                    <span>
                      {item.quantity}x {item.display_name ?? "Producto"}
                      {item.notes && (
                        <span className="ml-1 text-gray-400 text-xs">({item.notes})</span>
                      )}
                    </span>
                    <span className="text-gray-600">
                      {formatCurrency(item.unit_price * item.quantity)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex justify-between text-sm font-semibold mt-2 pt-2 border-t border-border">
              <span>Total</span>
              <span>{formatCurrency(pedido.total_amount)}</span>
            </div>
            {pedido.credit_applied > 0 && (
              <div className="flex justify-between text-xs text-purple-600 mt-1">
                <span>Crédito aplicado</span>
                <span>-{formatCurrency(pedido.credit_applied)}</span>
              </div>
            )}
          </section>

          {/* Incidencias activas */}
          {pedido.incidents.filter((i) => i.status === "open" || i.status === "in_review").length > 0 && (
            <section className="bg-rose-50 rounded-xl p-3 border border-rose-200">
              <h3 className="text-sm font-semibold text-rose-700 flex items-center gap-1 mb-2">
                <AlertTriangle className="h-4 w-4" /> Incidencias
              </h3>
              {pedido.incidents
                .filter((i) => i.status === "open" || i.status === "in_review")
                .map((inc) => (
                  <div key={inc.id} className="text-sm text-rose-700 mb-2">
                    <div className="font-medium">{INCIDENT_TYPE_LABELS[inc.type] ?? inc.type}</div>
                    {inc.description && (
                      <div className="text-xs text-rose-600">{inc.description}</div>
                    )}
                    {["cashier", "admin", "owner"].includes(userRole) && (
                      <button
                        className="mt-1 text-xs border border-rose-300 text-rose-700 px-2 py-1 rounded-lg hover:bg-rose-50 transition-colors"
                        onClick={() => handleResolveRedispatch(inc.id)}
                      >
                        Re-despacho
                      </button>
                    )}
                  </div>
                ))}
            </section>
          )}

          {/* Historial de estados */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Historial</h3>
            <ol className="space-y-2">
              {pedido.status_history.map((h, i) => (
                <li key={h.id} className="flex items-start gap-2 text-sm">
                  <span
                    className={`mt-1.5 h-2 w-2 rounded-full shrink-0 ${
                      i === pedido.status_history.length - 1 ? "bg-brand" : "bg-gray-300"
                    }`}
                  />
                  <div>
                    <span className="text-gray-700">
                      {ORDER_STATUS_LABELS[h.new_status as keyof typeof ORDER_STATUS_LABELS] ?? h.new_status}
                    </span>
                    {h.note && <span className="ml-1 text-gray-400 text-xs">— {h.note}</span>}
                    <div className="text-xs text-gray-400">
                      {formatDateTime(h.changed_at)}
                      {h.changed_by_name && ` · ${h.changed_by_name}`}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          {/* Notas de preparación y entrega (solo lectura, cargadas al crear el pedido) */}
          {(pedido.kitchen_notes || pedido.delivery_notes) && (
            <section className="space-y-1">
              {pedido.kitchen_notes && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-sm">
                  <p className="text-xs font-semibold text-amber-700 mb-0.5">Notas de preparación</p>
                  <p className="text-amber-900">{pedido.kitchen_notes}</p>
                </div>
              )}
              {pedido.delivery_notes && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 text-sm">
                  <p className="text-xs font-semibold text-blue-700 mb-0.5">Notas de entrega</p>
                  <p className="text-blue-900">{pedido.delivery_notes}</p>
                </div>
              )}
            </section>
          )}

          {/* Notas internas */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-1">Notas internas</h3>
            <textarea
              className="w-full border border-border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 resize-none"
              value={notes}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setNotes(e.target.value)}
              placeholder="Solo visibles para el personal..."
              rows={2}
            />
            <button
              className="mt-1 btn-outline px-3 py-1.5 text-xs rounded-xl disabled:opacity-50"
              disabled={savingNotes}
              onClick={handleSaveNotes}
            >
              {savingNotes ? "Guardando..." : "Guardar notas"}
            </button>
          </section>
        </div>

        {/* Pie con acciones */}
        <div className="border-t border-border px-5 py-3 flex flex-wrap gap-2">
          {advanceAllowed() && nextStatus && (
            <button
              className="flex-1 btn-primary gap-1 flex items-center justify-center rounded-xl disabled:opacity-50"
              disabled={advancing}
              onClick={handleAdvance}
            >
              {advancing ? "..." : (NEXT_STATUS_BUTTON_LABELS[pedido.status] ?? "Avanzar")}
              <ChevronRight className="h-4 w-4" />
            </button>
          )}

          {canMarkPaid && pedido.payment_status === "pending_payment" && (
            <button
              className="btn-outline px-3 py-2 text-sm rounded-xl"
              onClick={handleMarkPaid}
            >
              Marcar pagado
            </button>
          )}

          {canGeneratePayLink && !pagoLink && (
            <button
              className="btn-outline px-3 py-2 text-sm rounded-xl flex items-center gap-1.5"
              onClick={handleGenerarLink}
              disabled={generandoLink}
            >
              <Link2 className="h-4 w-4" />
              {generandoLink ? "Generando…" : "Link de pago"}
            </button>
          )}

          {pagoLink && (
            <div className="w-full flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-xl px-3 py-2 text-xs">
              <span className="flex-1 truncate text-blue-700">{pagoLink}</span>
              <button
                onClick={handleCopiarLink}
                className="shrink-0 flex items-center gap-1 text-blue-600 hover:text-blue-800 font-medium"
                title="Copiar link"
              >
                {linkCopiado ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                {linkCopiado ? "Copiado" : "Copiar"}
              </button>
            </div>
          )}

          {canReportIncident &&
            ["in_delivery", "to_dispatch", "in_preparation"].includes(pedido.status) && (
              <button
                className="px-3 py-2 text-sm border border-rose-300 text-rose-600 rounded-xl hover:bg-rose-50 transition-colors"
                onClick={() => setShowIncidencia(true)}
              >
                Reportar incidencia
              </button>
            )}

          {canCancel && (
            <button
              className="px-3 py-2 text-sm border border-red-300 text-red-600 rounded-xl hover:bg-red-50 transition-colors"
              onClick={() => setShowCancel(true)}
            >
              Cancelar pedido
            </button>
          )}
        </div>
      </div>

      {showCancel && (
        <CancelarModal
          pedido={pedido}
          comercioId={comercioId}
          onClose={() => setShowCancel(false)}
          onCancelled={(updated) => {
            setShowCancel(false)
            onUpdated(updated)
          }}
        />
      )}

      {showIncidencia && (
        <IncidenciaModal
          pedido={pedido}
          comercioId={comercioId}
          onClose={() => setShowIncidencia(false)}
          onReported={(updated) => {
            setShowIncidencia(false)
            onUpdated(updated)
          }}
        />
      )}
    </>
  )
}
