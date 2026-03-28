"use client"

/**
 * Página de alta del primer comercio.
 * Solo accesible para dueños recién registrados que aún no tienen comercios.
 */
import { useState } from "react"
import { useRouter } from "next/navigation"
import { api, ApiError } from "@/lib/api"

export default function NuevoComercioPage() {
  const router = useRouter()
  const [name, setName] = useState("")
  const [address, setAddress] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const comercio = await api.comercios.crear({
        name,
        address: address || undefined,
      })
      localStorage.setItem("comercio_id", comercio.id)
      localStorage.setItem("comercio_name", comercio.name)
      router.push(`/${comercio.id}/pedidos`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ocurrió un error. Intentá de nuevo.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card p-8">
      <h1 className="font-serif text-3xl text-brown mb-2">Crear tu comercio</h1>
      <p className="text-brown-muted text-sm mb-8">
        Completá los datos básicos de tu pizzería. Podrás editarlos después desde los ajustes.
      </p>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-semibold text-brown mb-1.5" htmlFor="name">
            Nombre del comercio
          </label>
          <input
            id="name"
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full border border-border rounded-xl px-4 py-3 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand transition-colors"
            placeholder="Pizzería Don Juan"
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-brown mb-1.5" htmlFor="address">
            Dirección / localidad{" "}
            <span className="font-normal text-brown-muted">(opcional)</span>
          </label>
          <input
            id="address"
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            className="w-full border border-border rounded-xl px-4 py-3 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand transition-colors"
            placeholder="Av. Corrientes 1234, CABA"
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
          {loading ? "Creando..." : "Crear comercio"}
        </button>
      </form>
    </div>
  )
}
