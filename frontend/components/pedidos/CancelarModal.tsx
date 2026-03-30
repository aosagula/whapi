"use client"

/**
 * Modal de confirmación de cancelación de pedido con política de pago.
 */

import { useState } from "react"
import { X } from "lucide-react"
import { api, type OrderResponse } from "@/lib/api"
import { formatCurrency } from "./order-utils"

interface Props {
  pedido: OrderResponse
  comercioId: string
  onClose: () => void
  onCancelled: (updated: OrderResponse) => void
}

function getPolicyInfo(pedido: OrderResponse): { label: string; detail: string } {
  if (["in_progress", "pending_payment"].includes(pedido.status)) {
    return { label: "Sin cargo", detail: "El cliente no será cobrado." }
  }
  if (
    ["pending_preparation", "in_preparation"].includes(pedido.status) &&
    pedido.payment_status === "paid"
  ) {
    return {
      label: "Crédito a favor",
      detail: `Se acreditarán ${formatCurrency(pedido.total_amount)} al cliente para su próxima compra.`,
    }
  }
  return { label: "Sin cargo", detail: "El cliente no fue cobrado." }
}

export default function CancelarModal({ pedido, comercioId, onClose, onCancelled }: Props) {
  const [note, setNote] = useState("")
  const [loading, setLoading] = useState(false)
  const policy = getPolicyInfo(pedido)

  async function handleConfirm() {
    setLoading(true)
    try {
      const updated = await api.pedidos.cancelar(comercioId, pedido.id, {
        note: note || undefined,
      })
      onCancelled(updated)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 space-y-4">
        {/* Encabezado */}
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-brown">Cancelar pedido #{pedido.order_number}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Política */}
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-sm">
          <div className="font-semibold text-amber-800">{policy.label}</div>
          <div className="text-amber-700 text-xs mt-0.5">{policy.detail}</div>
        </div>

        {/* Motivo */}
        <textarea
          className="w-full border border-border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 resize-none"
          placeholder="Motivo de la cancelación (opcional)"
          rows={2}
          value={note}
          onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setNote(e.target.value)}
        />

        {/* Acciones */}
        <div className="flex gap-2 justify-end">
          <button
            className="btn-outline px-4 py-2 text-sm rounded-xl"
            onClick={onClose}
            disabled={loading}
          >
            Volver
          </button>
          <button
            className="bg-red-600 hover:bg-red-700 text-white font-semibold px-4 py-2 text-sm rounded-xl transition-colors disabled:opacity-50"
            onClick={handleConfirm}
            disabled={loading}
          >
            {loading ? "Cancelando..." : "Confirmar cancelación"}
          </button>
        </div>
      </div>
    </div>
  )
}
