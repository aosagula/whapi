"use client"

/**
 * Tablero de pedidos en tiempo real.
 */

import { useParams } from "next/navigation"
import TablaPedidos from "@/components/pedidos/TablaPedidos"

export default function PedidosPage() {
  const params = useParams()
  const comercioId = params.comercio_id as string
  // El rol se guarda en localStorage al seleccionar el comercio
  const userRole =
    typeof window !== "undefined" ? (localStorage.getItem("comercio_role") ?? "cashier") : "cashier"

  return (
    <div>
      <div className="mb-6">
        <h1 className="font-serif text-3xl text-brown">Pedidos</h1>
        <p className="text-brown-muted text-sm mt-1">Gestión de pedidos en tiempo real</p>
      </div>
      <TablaPedidos comercioId={comercioId} userRole={userRole} />
    </div>
  )
}
