/**
 * Utilidades para mostrar estados de pedidos en la UI.
 */

import type { OrderStatus, PaymentStatus } from "@/lib/api"

// Etiquetas en español para cada estado
export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  in_progress: "En curso",
  pending_payment: "Pend. pago",
  pending_preparation: "Pend. prep.",
  in_preparation: "En prep.",
  to_dispatch: "A despacho",
  in_delivery: "En camino",
  delivered: "Entregado",
  cancelled: "Cancelado",
  with_incident: "Con incidencia",
  discarded: "Descartado",
}

// Color de badge por estado
export const ORDER_STATUS_COLORS: Record<OrderStatus, string> = {
  in_progress: "bg-slate-100 text-slate-700",
  pending_payment: "bg-yellow-100 text-yellow-700",
  pending_preparation: "bg-amber-100 text-amber-700",
  in_preparation: "bg-blue-100 text-blue-700",
  to_dispatch: "bg-orange-100 text-orange-700",
  in_delivery: "bg-indigo-100 text-indigo-700",
  delivered: "bg-green-100 text-green-700",
  cancelled: "bg-red-100 text-red-700",
  with_incident: "bg-rose-100 text-rose-800",
  discarded: "bg-slate-100 text-slate-400",
}

// Etiquetas de estado de pago
export const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
  paid: "Pagado",
  cash_on_delivery: "Efectivo destino",
  pending_payment: "Pend. pago",
  credit: "Crédito a favor",
  refunded: "Reembolsado",
  no_charge: "Sin cargo",
}

export const PAYMENT_STATUS_COLORS: Record<PaymentStatus, string> = {
  paid: "bg-green-100 text-green-700",
  cash_on_delivery: "bg-slate-100 text-slate-600",
  pending_payment: "bg-yellow-100 text-yellow-700",
  credit: "bg-purple-100 text-purple-700",
  refunded: "bg-blue-100 text-blue-700",
  no_charge: "bg-slate-100 text-slate-500",
}

// Etiquetas de tipo de entrega
export const DELIVERY_TYPE_LABELS: Record<string, string> = {
  delivery: "Delivery",
  pickup: "Retiro en local",
}

// Etiquetas de origen del pedido
export const ORIGIN_LABELS: Record<string, string> = {
  whatsapp: "WhatsApp",
  phone: "Telefónico",
  operator: "Operador",
}

// Transiciones permitidas por estado actual (para mostrar el botón "avanzar")
export const NEXT_STATUS: Partial<Record<OrderStatus, OrderStatus>> = {
  pending_preparation: "in_preparation",
  in_preparation: "to_dispatch",
  to_dispatch: "in_delivery",
  in_delivery: "delivered",
}

// Etiquetas para los botones de avance
export const NEXT_STATUS_BUTTON_LABELS: Partial<Record<OrderStatus, string>> = {
  pending_preparation: "Iniciar preparación",
  in_preparation: "Listo para despacho",
  to_dispatch: "En camino",
  in_delivery: "Marcar entregado",
}

// Etiquetas de tipos de incidencia
export const INCIDENT_TYPE_LABELS: Record<string, string> = {
  wrong_address: "Dirección incorrecta",
  wrong_order: "Pedido equivocado",
  missing_item: "Producto faltante",
  bad_condition: "Producto en mal estado",
  customer_not_found: "Cliente no encontrado",
  other: "Otro",
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS" }).format(amount)
}

export function formatTime(isoDate: string): string {
  return new Date(isoDate).toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" })
}

export function formatDateTime(isoDate: string): string {
  return new Date(isoDate).toLocaleString("es-AR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  })
}
