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

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
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
  is_active: boolean
  role: string
}

export interface MisComerciosResponse {
  comercios: ComercioResponse[]
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
  },
}
