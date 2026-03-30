"use client"

/**
 * Modal para reportar una incidencia en un pedido.
 */

import { useState } from "react"
import { X } from "lucide-react"
import { api, type OrderResponse } from "@/lib/api"
import { INCIDENT_TYPE_LABELS } from "./order-utils"

interface Props {
  pedido: OrderResponse
  comercioId: string
  onClose: () => void
  onReported: (updated: OrderResponse) => void
}

export default function IncidenciaModal({ pedido, comercioId, onClose, onReported }: Props) {
  const [type, setType] = useState("")
  const [description, setDescription] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit() {
    if (!type) return
    setLoading(true)
    try {
      const updated = await api.pedidos.reportarIncidencia(comercioId, pedido.id, {
        type,
        description: description || undefined,
      })
      onReported(updated)
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
          <h2 className="font-semibold text-brown">Reportar incidencia — Pedido #{pedido.order_number}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tipo */}
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-1">Tipo de incidencia</label>
          <select
            className="w-full border border-border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 bg-white"
            value={type}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setType(e.target.value)}
          >
            <option value="">Seleccioná el tipo...</option>
            {Object.entries(INCIDENT_TYPE_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {/* Descripción */}
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-1">Descripción (opcional)</label>
          <textarea
            className="w-full border border-border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 resize-none"
            value={description}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDescription(e.target.value)}
            placeholder="Describí el problema..."
            rows={2}
          />
        </div>

        {/* Acciones */}
        <div className="flex gap-2 justify-end">
          <button
            className="btn-outline px-4 py-2 text-sm rounded-xl"
            onClick={onClose}
            disabled={loading}
          >
            Cancelar
          </button>
          <button
            className="btn-primary px-4 py-2 text-sm rounded-xl disabled:opacity-50"
            onClick={handleSubmit}
            disabled={loading || !type}
          >
            {loading ? "Reportando..." : "Reportar incidencia"}
          </button>
        </div>
      </div>
    </div>
  )
}
