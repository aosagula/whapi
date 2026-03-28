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
  product_id: string
  quantity: number
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
      data: { code: string; short_name: string; full_name: string; description?: string; price: number; is_available?: boolean; items?: { product_id: string; quantity: number }[] },
    ) =>
      request<ComboResponse>(`/comercios/${comercioId}/combos`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    editar: (
      comercioId: string,
      comboId: string,
      data: { short_name?: string; full_name?: string; description?: string; price?: number; is_available?: boolean; items?: { product_id: string; quantity: number }[] },
    ) =>
      request<ComboResponse>(`/comercios/${comercioId}/combos/${comboId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    eliminar: (comercioId: string, comboId: string) =>
      request<void>(`/comercios/${comercioId}/combos/${comboId}`, { method: "DELETE" }),
  },
}
