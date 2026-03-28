"use client"

/**
 * Página de login.
 * Autentica al usuario, guarda el token y redirige al selector de comercios.
 */
import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { api, ApiError } from "@/lib/api"

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const { access_token } = await api.auth.login({ email, password })

      // Guardar en localStorage y en cookie (para el middleware de Next.js)
      localStorage.setItem("access_token", access_token)
      document.cookie = `access_token=${access_token}; path=/; max-age=3600; SameSite=Lax`

      router.push("/selector")
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Email o contraseña incorrectos")
      } else {
        setError("Ocurrió un error. Intentá de nuevo.")
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card p-8">
      <h1 className="font-serif text-3xl text-brown mb-2">Iniciá sesión</h1>
      <p className="text-brown-muted text-sm mb-8">Ingresá a tu cuenta de Whapi</p>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-semibold text-brown mb-1.5" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full border border-border rounded-xl px-4 py-3 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand transition-colors"
            placeholder="tu@email.com"
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-brown mb-1.5" htmlFor="password">
            Contraseña
          </label>
          <input
            id="password"
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full border border-border rounded-xl px-4 py-3 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand transition-colors"
            placeholder="••••••••"
          />
        </div>

        {error && (
          <p role="alert" className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full py-3 text-base disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {loading ? "Ingresando..." : "Ingresar"}
        </button>
      </form>

      <p className="text-center text-sm text-brown-muted mt-6">
        ¿No tenés cuenta?{" "}
        <Link href="/registro" className="text-brand font-semibold hover:underline">
          Registrate
        </Link>
      </p>
    </div>
  )
}
