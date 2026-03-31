"use client"

/**
 * Vista de delivery: muestra pedidos a despacho y en camino,
 * agrupados por estado, con botón de avance rápido.
 * La dirección completa se consulta abriendo el panel de detalle.
 */

import { useState, useEffect, useCallback } from "react"
import { RefreshCw, Clock, Phone, MapPin } from "lucide-react"
import { api, type OrderListItem, type OrderResponse, type OrderStatus } from "@/lib/api"
import {
  ORDER_STATUS_LABELS,
  ORDER_STATUS_COLORS,
  NEXT_STATUS,
  NEXT_STATUS_BUTTON_LABELS,
  DELIVERY_TYPE_LABELS,
  formatTime,
} from "./order-utils"
import PedidoDetalle from "./PedidoDetalle"

interface Props {
  comercioId: string
  userRole: string
}

const DELIVERY_STATUSES: OrderStatus[] = ["to_dispatch", "in_delivery"]

export default function VistaDelivery({ comercioId, userRole }: Props) {
  const [pedidosPorEstado, setPedidosPorEstado] = useState<Record<string, OrderListItem[]>>({})
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [advancing, setAdvancing] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detalle, setDetalle] = useState<OrderResponse | null>(null)
  const [loadingDetalle, setLoadingDetalle] = useState(false)

  const fetchAll = useCallback(
    async (showRefreshing = false) => {
      if (showRefreshing) setRefreshing(true)
      else setLoading(true)
      try {
        const results = await Promise.all(
          DELIVERY_STATUSES.map((status) => api.pedidos.listar(comercioId, { status, page_size: 50 })),
        )
        const byStatus: Record<string, OrderListItem[]> = {}
        DELIVERY_STATUSES.forEach((status, i) => {
          byStatus[status] = results[i].items
        })
        setPedidosPorEstado(byStatus)
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [comercioId],
  )

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  async function handleAdvance(pedidoId: string, nextStatus: OrderStatus) {
    setAdvancing(pedidoId)
    try {
      await api.pedidos.cambiarEstado(comercioId, pedidoId, nextStatus)
      fetchAll(true)
    } finally {
      setAdvancing(null)
    }
  }

  async function openDetalle(id: string) {
    setSelectedId(id)
    setLoadingDetalle(true)
    try {
      const data = await api.pedidos.obtener(comercioId, id)
      setDetalle(data)
    } finally {
      setLoadingDetalle(false)
    }
  }

  function handleUpdated(updated: OrderResponse) {
    setDetalle(updated)
    fetchAll(true)
  }

  if (loading) return <div className="text-center py-12 text-gray-400">Cargando...</div>

  const allEmpty = DELIVERY_STATUSES.every((s) => (pedidosPorEstado[s]?.length ?? 0) === 0)

  return (
    <div className="space-y-6">
      {/* Barra de acciones */}
      <div className="flex justify-end">
        <button
          title="Actualizar"
          onClick={() => fetchAll(true)}
          disabled={refreshing}
          className="p-2 border border-border rounded-xl hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 text-gray-500 ${refreshing ? "animate-spin" : ""}`} />
        </button>
      </div>

      {allEmpty ? (
        <div className="text-center py-16 text-gray-400">No hay pedidos en delivery.</div>
      ) : (
        DELIVERY_STATUSES.map((status) => {
          const items = pedidosPorEstado[status] ?? []
          if (items.length === 0) return null
          const nextSt = NEXT_STATUS[status]
          const canAdvance =
            !!nextSt &&
            (userRole === "delivery" || ["cashier", "admin", "owner"].includes(userRole))

          return (
            <div key={status}>
              <div className="flex items-center gap-2 mb-3">
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-medium ${ORDER_STATUS_COLORS[status]}`}
                >
                  {ORDER_STATUS_LABELS[status]}
                </span>
                <span className="text-xs text-gray-400">{items.length} pedido{items.length !== 1 ? "s" : ""}</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {items.map((pedido) => (
                  <div
                    key={pedido.id}
                    className="card p-4 space-y-3 hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => openDetalle(pedido.id)}
                  >
                    {/* Encabezado */}
                    <div className="flex items-start justify-between">
                      <span className="font-mono text-xs text-gray-400">#{pedido.order_number}</span>
                      <div className="flex items-center gap-1 text-xs text-gray-400">
                        <Clock className="h-3 w-3" />
                        {formatTime(pedido.created_at)}
                      </div>
                    </div>

                    {/* Cliente */}
                    <div>
                      <div className="font-medium text-brown text-sm">
                        {pedido.customer.name ?? "Sin nombre"}
                      </div>
                      <div className="flex items-center gap-1 text-xs text-gray-400 mt-0.5">
                        <Phone className="h-3 w-3" />
                        {pedido.customer.phone}
                      </div>
                    </div>

                    {/* Tipo de entrega */}
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <MapPin className="h-3 w-3" />
                      {DELIVERY_TYPE_LABELS[pedido.delivery_type] ?? pedido.delivery_type}
                      {pedido.delivery_type === "delivery" && (
                        <span className="text-gray-400 ml-1">· Ver dirección en detalle</span>
                      )}
                    </div>

                    {/* Items */}
                    <div className="text-xs text-gray-400 line-clamp-2">
                      {pedido.items_summary.join(", ") || "—"}
                    </div>

                    {/* Botón avanzar */}
                    {canAdvance && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleAdvance(pedido.id, nextSt!)
                        }}
                        disabled={advancing === pedido.id}
                        className="w-full btn-primary text-xs py-1.5 rounded-lg disabled:opacity-50"
                      >
                        {advancing === pedido.id
                          ? "Guardando..."
                          : NEXT_STATUS_BUTTON_LABELS[status]}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )
        })
      )}

      {/* Panel de detalle lateral */}
      {selectedId &&
        (loadingDetalle ? (
          <>
            <div className="fixed inset-0 bg-black/40 z-40" onClick={() => setSelectedId(null)} />
            <div className="fixed right-0 top-0 h-full w-full max-w-lg bg-white z-50 shadow-xl flex items-center justify-center">
              <span className="text-gray-400">Cargando...</span>
            </div>
          </>
        ) : detalle ? (
          <PedidoDetalle
            pedido={detalle}
            comercioId={comercioId}
            userRole={userRole}
            onClose={() => {
              setSelectedId(null)
              setDetalle(null)
            }}
            onUpdated={handleUpdated}
          />
        ) : null)}
    </div>
  )
}
