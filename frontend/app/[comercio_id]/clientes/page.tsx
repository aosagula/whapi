"use client"

/**
 * Listado de clientes del comercio con búsqueda y paginación.
 */
import { useEffect, useState, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { Search, Users, ChevronLeft, ChevronRight } from "lucide-react"
import { api, ClienteResponse } from "@/lib/api"

const PAGE_SIZE = 20

export default function ClientesPage() {
  const params = useParams()
  const router = useRouter()
  const comercioId = params.comercio_id as string

  const [clientes, setClientes] = useState<ClienteResponse[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [query, setQuery] = useState("")
  const [inputValue, setInputValue] = useState("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const cargar = useCallback(async (q: string, p: number) => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.clientes.listar(comercioId, { q: q || undefined, page: p, page_size: PAGE_SIZE })
      setClientes(data.items)
      setTotal(data.total)
    } catch {
      setError("No se pudo cargar la lista de clientes.")
    } finally {
      setLoading(false)
    }
  }, [comercioId])

  useEffect(() => {
    cargar(query, page)
  }, [cargar, query, page])

  function handleBuscar(e: React.FormEvent) {
    e.preventDefault()
    setPage(1)
    setQuery(inputValue)
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div>
      <div className="mb-6">
        <h1 className="font-serif text-3xl text-brown">Clientes</h1>
        <p className="text-brown-muted text-sm mt-1">
          {total > 0
            ? `${total} cliente${total !== 1 ? "s" : ""} registrado${total !== 1 ? "s" : ""}`
            : "Sin clientes registrados"}
        </p>
      </div>

      {/* Buscador */}
      <form onSubmit={handleBuscar} className="mb-4 flex gap-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-brown-muted" />
          <input
            type="text"
            placeholder="Buscar por nombre o teléfono..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-stone-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
        </div>
        <button
          type="submit"
          className="px-4 py-2 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600 transition-colors"
        >
          Buscar
        </button>
        {query && (
          <button
            type="button"
            onClick={() => { setInputValue(""); setQuery(""); setPage(1) }}
            className="px-4 py-2 border border-stone-200 rounded-lg text-sm text-brown-muted hover:bg-stone-50 transition-colors"
          >
            Limpiar
          </button>
        )}
      </form>

      {/* Tabla */}
      <div className="bg-white border border-stone-200 rounded-2xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-16 flex flex-col items-center gap-3 text-brown-muted">
            <div className="w-6 h-6 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">Cargando clientes...</span>
          </div>
        ) : error ? (
          <div className="py-16 text-center text-red-500 text-sm">{error}</div>
        ) : clientes.length === 0 ? (
          <div className="py-16 flex flex-col items-center gap-3 text-brown-muted">
            <Users className="w-10 h-10 opacity-30" />
            <p className="text-sm">
              {query
                ? "No se encontraron clientes con ese criterio."
                : "Todavía no hay clientes registrados."}
            </p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-stone-50 border-b border-stone-200">
              <tr>
                <th className="text-left px-4 py-3 text-brown-muted font-medium">Cliente</th>
                <th className="text-left px-4 py-3 text-brown-muted font-medium">Teléfono</th>
                <th className="text-left px-4 py-3 text-brown-muted font-medium">LID WhatsApp</th>
                <th className="text-right px-4 py-3 text-brown-muted font-medium">Crédito</th>
                <th className="text-left px-4 py-3 text-brown-muted font-medium">Alta</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {clientes.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => router.push(`/${comercioId}/clientes/${c.id}`)}
                  className="hover:bg-amber-50 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-brown">
                      {c.display_name ?? <span className="text-brown-muted italic font-normal">Sin nombre</span>}
                    </div>
                    {c.ai_name && c.ai_name !== c.display_name && (
                      <div className="text-xs text-brown-muted">Perfil WA: {c.ai_name}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-brown-muted">{c.phone_display ?? "—"}</td>
                  <td className="px-4 py-3 text-brown-muted">{c.whatsapp_lid ?? "—"}</td>
                  <td className="px-4 py-3 text-right">
                    {c.credit_balance > 0 ? (
                      <span className="inline-block bg-green-100 text-green-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                        ${c.credit_balance.toFixed(2)}
                      </span>
                    ) : (
                      <span className="text-brown-muted">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-brown-muted">
                    {new Date(c.created_at).toLocaleDateString("es-AR", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Paginación */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between text-sm text-brown-muted">
          <span>Página {page} de {totalPages}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-2 rounded-lg border border-stone-200 hover:bg-stone-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-2 rounded-lg border border-stone-200 hover:bg-stone-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
