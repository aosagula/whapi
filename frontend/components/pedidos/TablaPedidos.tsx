"use client"

/**
 * Tablero de pedidos: lista con filtros, refresh y panel de detalle lateral.
 */

import { useState, useEffect, useCallback } from "react"
import { RefreshCw, Search } from "lucide-react"
import { api, type OrderListItem, type OrderResponse, type OrderStatus, type PaymentStatus } from "@/lib/api"
import {
  ORDER_STATUS_LABELS,
  ORDER_STATUS_COLORS,
  PAYMENT_STATUS_LABELS,
  PAYMENT_STATUS_COLORS,
  DELIVERY_TYPE_LABELS,
  formatCurrency,
  formatTime,
} from "./order-utils"
import PedidoDetalle from "./PedidoDetalle"

interface Props {
  comercioId: string
  userRole: string
}

const STATUS_OPTIONS = [
  { value: "", label: "Todos los estados" },
  { value: "pending_preparation", label: "Pend. preparación" },
  { value: "in_preparation", label: "En preparación" },
  { value: "to_dispatch", label: "A despacho" },
  { value: "in_delivery", label: "En camino" },
  { value: "delivered", label: "Entregado" },
  { value: "cancelled", label: "Cancelado" },
  { value: "with_incident", label: "Con incidencia" },
]

const PAYMENT_OPTIONS = [
  { value: "", label: "Todos los pagos" },
  { value: "paid", label: "Pagado" },
  { value: "cash_on_delivery", label: "Efectivo destino" },
  { value: "pending_payment", label: "Pend. pago" },
  { value: "no_charge", label: "Sin cargo" },
]

export default function TablaPedidos({ comercioId, userRole }: Props) {
  const [pedidos, setPedidos] = useState<OrderListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [statusFilter, setStatusFilter] = useState("")
  const [paymentFilter, setPaymentFilter] = useState("")
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detalle, setDetalle] = useState<OrderResponse | null>(null)
  const [loadingDetalle, setLoadingDetalle] = useState(false)

  const pageSize = 20

  const fetchPedidos = useCallback(
    async (showRefreshing = false) => {
      if (showRefreshing) setRefreshing(true)
      else setLoading(true)
      setError(null)
      try {
        const data = await api.pedidos.listar(comercioId, {
          status: statusFilter || undefined,
          payment_status: paymentFilter || undefined,
          page,
          page_size: pageSize,
        })
        setPedidos(data.items)
        setTotal(data.total)
      } catch {
        setError("No se pudieron cargar los pedidos")
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [comercioId, statusFilter, paymentFilter, page],
  )

  useEffect(() => {
    fetchPedidos()
  }, [fetchPedidos])

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
    fetchPedidos(true)
  }

  const filteredPedidos = search
    ? pedidos.filter(
        (p) =>
          p.customer.phone.includes(search) ||
          (p.customer.name ?? "").toLowerCase().includes(search.toLowerCase()),
      )
    : pedidos

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-4">
      {/* Barra de herramientas */}
      <div className="flex flex-col sm:flex-row gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar cliente o teléfono..."
            value={search}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand/30"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
            setStatusFilter(e.target.value)
            setPage(1)
          }}
          className="border border-border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 bg-white"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        <select
          value={paymentFilter}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
            setPaymentFilter(e.target.value)
            setPage(1)
          }}
          className="border border-border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 bg-white"
        >
          {PAYMENT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        <button
          title="Actualizar"
          onClick={() => fetchPedidos(true)}
          disabled={refreshing}
          className="p-2 border border-border rounded-xl hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 text-gray-500 ${refreshing ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Contador */}
      <p className="text-sm text-gray-500">
        {total} pedido{total !== 1 ? "s" : ""}
        {(statusFilter || paymentFilter) ? " (con filtros)" : ""}
      </p>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Tabla */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">Cargando pedidos...</div>
      ) : filteredPedidos.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          {search ? "Sin coincidencias." : "No hay pedidos para mostrar."}
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-border">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600 w-16">#</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Cliente</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600 hidden md:table-cell">Hora</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600 hidden lg:table-cell">Productos</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Total</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Estado</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredPedidos.map((pedido) => (
                <tr
                  key={pedido.id}
                  className="hover:bg-[#faf7f2] cursor-pointer transition-colors"
                  onClick={() => openDetalle(pedido.id)}
                >
                  <td className="px-4 py-3 font-mono text-gray-400 text-xs">
                    #{pedido.order_number}
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-brown">{pedido.customer.name ?? "Sin nombre"}</div>
                    <div className="text-gray-400 text-xs">{pedido.customer.phone}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-500 hidden md:table-cell">
                    <div>{formatTime(pedido.created_at)}</div>
                    <div className="text-xs text-gray-400">{DELIVERY_TYPE_LABELS[pedido.delivery_type] ?? pedido.delivery_type}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-500 hidden lg:table-cell">
                    <div className="max-w-[200px] truncate text-xs">
                      {pedido.items_summary.join(", ") || "—"}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-brown">
                    {formatCurrency(pedido.total_amount)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="space-y-1">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                          ORDER_STATUS_COLORS[pedido.status as OrderStatus] ?? "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {ORDER_STATUS_LABELS[pedido.status as OrderStatus] ?? pedido.status}
                      </span>
                      <div>
                        <span
                          className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                            PAYMENT_STATUS_COLORS[pedido.payment_status as PaymentStatus] ?? "bg-gray-100 text-gray-500"
                          }`}
                        >
                          {PAYMENT_STATUS_LABELS[pedido.payment_status as PaymentStatus] ?? pedido.payment_status}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="text-xs text-brand hover:underline">Ver detalle</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Paginación */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-3">
          <button
            className="btn-outline px-4 py-1.5 text-sm rounded-xl disabled:opacity-40"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Anterior
          </button>
          <span className="text-sm text-gray-500">
            Página {page} de {totalPages}
          </span>
          <button
            className="btn-outline px-4 py-1.5 text-sm rounded-xl disabled:opacity-40"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Siguiente
          </button>
        </div>
      )}

      {/* Panel de detalle lateral */}
      {selectedId && (
        loadingDetalle ? (
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
            onClose={() => { setSelectedId(null); setDetalle(null) }}
            onUpdated={handleUpdated}
          />
        ) : null
      )}
    </div>
  )
}
