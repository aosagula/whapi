/**
 * Cliente HTTP para la API de Whapi.
 * Agrega automáticamente el token JWT del localStorage si está disponible.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = "ApiError"
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, body?.detail ?? res.statusText)
  }

  // 204 No Content
  if (res.status === 204) return undefined as unknown as T
  return res.json() as Promise<T>
}

// ── Tipos de respuesta ─────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface UserResponse {
  id: string
  name: string
  email: string
  phone: string | null
  is_active: boolean
  account_type: "owner" | "employee"
  created_at: string
}

export interface RegisterResponse extends UserResponse {
  token: TokenResponse
}

export interface ComercioResponse {
  id: string
  name: string
  address: string | null
  logo_url: string | null
  half_half_surcharge: string
  is_active: boolean
  role: string
}

export interface MisComerciosResponse {
  comercios: ComercioResponse[]
}

export type RolComercio = "owner" | "admin" | "cashier" | "cook" | "delivery"

export interface EmpleadoResponse {
  user_id: string
  name: string
  email: string
  phone: string | null
  role: RolComercio
  is_active: boolean
  joined_at: string
}

// ── Catálogo ──────────────────────────────────────────────────────────────────

export type ProductCategory = "pizza" | "empanada" | "drink"

export interface CatalogItemData {
  id: string
  price_large: number | null
  price_small: number | null
  price_unit: number | null
  price_dozen: number | null
  is_available: boolean
}

export interface ProductResponse {
  id: string
  business_id: string
  code: string
  short_name: string
  full_name: string
  description: string | null
  category: ProductCategory
  is_available: boolean
  created_at: string
  updated_at: string
  catalog_item: CatalogItemData | null
}

export interface ProductListResponse {
  items: ProductResponse[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ComboItemResponse {
  id: string
  product_id: string | null
  quantity: number
  is_open: boolean
  open_category: ProductCategory | null
  product: ProductResponse | null
}

export interface ComboResponse {
  id: string
  business_id: string
  code: string
  short_name: string
  full_name: string
  description: string | null
  price: number
  is_available: boolean
  created_at: string
  updated_at: string
  items: ComboItemResponse[]
}

// ── Endpoints ─────────────────────────────────────────────────────────────────

export const api = {
  auth: {
    registro: (data: {
      name: string
      email: string
      password: string
      account_type: "owner" | "employee"
      phone?: string
    }) =>
      request<RegisterResponse>("/auth/registro", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    login: (data: { email: string; password: string }) =>
      request<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    me: () => request<UserResponse>("/auth/me"),
  },

  comercios: {
    misComercio: () => request<MisComerciosResponse>("/comercios/mis-comercios"),

    crear: (data: { name: string; address?: string; logo_url?: string }) =>
      request<ComercioResponse>("/comercios", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    detalle: (id: string) => request<ComercioResponse>(`/comercios/${id}`),

    editar: (id: string, data: Partial<{ name: string; address: string; logo_url: string; half_half_surcharge: number }>) =>
      request<ComercioResponse>(`/comercios/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
  },

  empleados: {
    listar: (comercioId: string) =>
      request<EmpleadoResponse[]>(`/comercios/${comercioId}/empleados`),

    asociar: (comercioId: string, data: { email: string; role: RolComercio }) =>
      request<EmpleadoResponse>(`/comercios/${comercioId}/empleados`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    cambiarRol: (comercioId: string, userId: string, role: RolComercio) =>
      request<EmpleadoResponse>(`/comercios/${comercioId}/empleados/${userId}`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      }),

    darDeBaja: (comercioId: string, userId: string) =>
      request<void>(`/comercios/${comercioId}/empleados/${userId}`, {
        method: "DELETE",
      }),
  },

  productos: {
    listar: (
      comercioId: string,
      params?: { category?: string; is_available?: boolean; search?: string; page?: number; page_size?: number },
    ) => {
      const q = new URLSearchParams()
      if (params?.category) q.set("category", params.category)
      if (params?.is_available !== undefined) q.set("is_available", String(params.is_available))
      if (params?.search) q.set("search", params.search)
      if (params?.page) q.set("page", String(params.page))
      if (params?.page_size) q.set("page_size", String(params.page_size))
      const qs = q.toString() ? `?${q.toString()}` : ""
      return request<ProductListResponse>(`/comercios/${comercioId}/products${qs}`)
    },

    crear: (
      comercioId: string,
      data: { code: string; short_name: string; full_name: string; description?: string; category: ProductCategory; is_available?: boolean },
    ) =>
      request<ProductResponse>(`/comercios/${comercioId}/products`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    editar: (
      comercioId: string,
      productId: string,
      data: { short_name?: string; full_name?: string; description?: string; is_available?: boolean },
    ) =>
      request<ProductResponse>(`/comercios/${comercioId}/products/${productId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    eliminar: (comercioId: string, productId: string) =>
      request<void>(`/comercios/${comercioId}/products/${productId}`, { method: "DELETE" }),

    crearOActualizarPrecios: (
      comercioId: string,
      data: { product_id: string; price_large?: number; price_small?: number; price_unit?: number; price_dozen?: number; is_available?: boolean },
    ) =>
      request<CatalogItemData>(`/comercios/${comercioId}/catalog`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  combos: {
    listar: (comercioId: string, params?: { is_available?: boolean; search?: string }) => {
      const q = new URLSearchParams()
      if (params?.is_available !== undefined) q.set("is_available", String(params.is_available))
      if (params?.search) q.set("search", params.search)
      const qs = q.toString() ? `?${q.toString()}` : ""
      return request<ComboResponse[]>(`/comercios/${comercioId}/combos${qs}`)
    },

    crear: (
      comercioId: string,
      data: {
        code: string; short_name: string; full_name: string; description?: string
        price: number; is_available?: boolean
        items?: ({ product_id: string; quantity: number; is_open: false } | { open_category: ProductCategory; quantity: number; is_open: true })[]
      },
    ) =>
      request<ComboResponse>(`/comercios/${comercioId}/combos`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    editar: (
      comercioId: string,
      comboId: string,
      data: {
        short_name?: string; full_name?: string; description?: string; price?: number; is_available?: boolean
        items?: ({ product_id: string; quantity: number; is_open: false } | { open_category: ProductCategory; quantity: number; is_open: true })[]
      },
    ) =>
      request<ComboResponse>(`/comercios/${comercioId}/combos/${comboId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    eliminar: (comercioId: string, comboId: string) =>
      request<void>(`/comercios/${comercioId}/combos/${comboId}`, { method: "DELETE" }),
  },

  pedidos: {
    crear: (
      comercioId: string,
      data: {
        customer_id: string
        origin: string
        delivery_type: string
        delivery_address?: string | null
        payment_status: string
        total_amount: number
        credit_applied?: number
        kitchen_notes?: string | null
        delivery_notes?: string | null
        items: {
          product_id?: string | null
          combo_id?: string | null
          quantity: number
          unit_price: number
          variant?: Record<string, unknown> | null
          notes?: string | null
        }[]
      },
    ) =>
      request<OrderResponse>(`/comercios/${comercioId}/pedidos`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    listar: (
      comercioId: string,
      params?: {
        status?: string
        payment_status?: string
        delivery_person_id?: string
        page?: number
        page_size?: number
      },
    ) => {
      const q = new URLSearchParams()
      if (params?.status) q.set("status", params.status)
      if (params?.payment_status) q.set("payment_status", params.payment_status)
      if (params?.delivery_person_id) q.set("delivery_person_id", params.delivery_person_id)
      if (params?.page) q.set("page", String(params.page))
      if (params?.page_size) q.set("page_size", String(params.page_size))
      const qs = q.toString() ? `?${q.toString()}` : ""
      return request<OrderListResponse>(`/comercios/${comercioId}/pedidos${qs}`)
    },

    obtener: (comercioId: string, pedidoId: string) =>
      request<OrderResponse>(`/comercios/${comercioId}/pedidos/${pedidoId}`),

    cambiarEstado: (comercioId: string, pedidoId: string, status: string, note?: string) =>
      request<OrderResponse>(`/comercios/${comercioId}/pedidos/${pedidoId}/estado`, {
        method: "PATCH",
        body: JSON.stringify({ status, note }),
      }),

    marcarPago: (comercioId: string, pedidoId: string, payment_status: string) =>
      request<OrderResponse>(`/comercios/${comercioId}/pedidos/${pedidoId}/pago`, {
        method: "PATCH",
        body: JSON.stringify({ payment_status }),
      }),

    asignarRepartidor: (
      comercioId: string,
      pedidoId: string,
      delivery_person_id: string | null,
    ) =>
      request<OrderResponse>(`/comercios/${comercioId}/pedidos/${pedidoId}/repartidor`, {
        method: "PATCH",
        body: JSON.stringify({ delivery_person_id }),
      }),

    actualizarNotas: (comercioId: string, pedidoId: string, internal_notes: string | null) =>
      request<OrderResponse>(`/comercios/${comercioId}/pedidos/${pedidoId}/notas`, {
        method: "PATCH",
        body: JSON.stringify({ internal_notes }),
      }),

    cancelar: (
      comercioId: string,
      pedidoId: string,
      data: { payment_policy?: string; note?: string },
    ) =>
      request<OrderResponse>(`/comercios/${comercioId}/pedidos/${pedidoId}/cancelar`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    reportarIncidencia: (
      comercioId: string,
      pedidoId: string,
      data: { type: string; description?: string },
    ) =>
      request<OrderResponse>(`/comercios/${comercioId}/pedidos/${pedidoId}/incidencia`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    resolverRedespacho: (comercioId: string, pedidoId: string, incidenciaId: string) =>
      request<OrderResponse>(
        `/comercios/${comercioId}/pedidos/${pedidoId}/incidencias/${incidenciaId}/redespacho`,
        { method: "POST", body: JSON.stringify({}) },
      ),
  },

  clientes: {
    buscarPorTelefono: (comercioId: string, phone: string) =>
      request<ClienteResponse>(`/comercios/${comercioId}/clientes/buscar?phone=${encodeURIComponent(phone)}`),

    crear: (comercioId: string, data: { phone: string; name?: string; address?: string; has_whatsapp?: boolean }) =>
      request<ClienteResponse>(`/comercios/${comercioId}/clientes`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    obtener: (comercioId: string, clienteId: string) =>
      request<ClienteResponse>(`/comercios/${comercioId}/clientes/${clienteId}`),

    actualizar: (comercioId: string, clienteId: string, data: { name?: string; address?: string; has_whatsapp?: boolean }) =>
      request<ClienteResponse>(`/comercios/${comercioId}/clientes/${clienteId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
  },
}

// ── Tipos de pedidos ──────────────────────────────────────────────────────────

export type OrderStatus =
  | "in_progress"
  | "pending_payment"
  | "pending_preparation"
  | "in_preparation"
  | "to_dispatch"
  | "in_delivery"
  | "delivered"
  | "cancelled"
  | "with_incident"
  | "discarded"

export type PaymentStatus =
  | "paid"
  | "cash_on_delivery"
  | "pending_payment"
  | "credit"
  | "refunded"
  | "no_charge"

export interface CustomerSummary {
  id: string
  name: string | null
  phone: string
}

export interface OrderItemResponse {
  id: string
  product_id: string | null
  combo_id: string | null
  quantity: number
  unit_price: number
  variant: Record<string, unknown> | null
  notes: string | null
  display_name: string | null
}

export interface StatusHistoryResponse {
  id: string
  previous_status: string | null
  new_status: string
  changed_by: string | null
  changed_by_name: string | null
  changed_at: string
  note: string | null
}

export interface IncidentResponse {
  id: string
  type: string
  description: string | null
  reported_by: string | null
  reported_by_name: string | null
  status: string
  resolved_at: string | null
  created_at: string
}

export interface OrderResponse {
  id: string
  business_id: string
  order_number: number
  customer: CustomerSummary
  status: OrderStatus
  payment_status: PaymentStatus
  origin: string
  delivery_type: string
  delivery_address: string | null
  total_amount: number
  credit_applied: number
  delivery_person_id: string | null
  internal_notes: string | null
  kitchen_notes: string | null
  delivery_notes: string | null
  created_by: string | null
  created_at: string
  updated_at: string
  items: OrderItemResponse[]
  status_history: StatusHistoryResponse[]
  incidents: IncidentResponse[]
}

export interface OrderListItem {
  id: string
  order_number: number
  customer: CustomerSummary
  status: OrderStatus
  payment_status: PaymentStatus
  origin: string
  delivery_type: string
  total_amount: number
  delivery_person_id: string | null
  created_at: string
  items_summary: string[]
}

export interface OrderListResponse {
  items: OrderListItem[]
  total: number
  page: number
  page_size: number
}

export interface ClienteResponse {
  id: string
  business_id: string
  phone: string
  name: string | null
  address: string | null
  has_whatsapp: boolean
  credit_balance: number
  created_at: string
}
