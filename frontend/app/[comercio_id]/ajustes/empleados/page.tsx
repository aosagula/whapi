"use client"

/**
 * Gestión de empleados del comercio.
 * Permite al owner/admin listar, asociar, cambiar rol y dar de baja empleados.
 */
import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { UserPlus, Trash2 } from "lucide-react"
import { api, ApiError, type EmpleadoResponse, type RolComercio } from "@/lib/api"

const ROLE_LABELS: Record<RolComercio, string> = {
  owner: "Dueño",
  admin: "Administrador",
  cashier: "Cajero",
  cook: "Cocinero",
  delivery: "Repartidor",
}

const ROLES_ASIGNABLES: RolComercio[] = ["admin", "cashier", "cook", "delivery"]

export default function EmpleadosPage() {
  const params = useParams()
  const comercioId = params.comercio_id as string

  const [empleados, setEmpleados] = useState<EmpleadoResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Formulario de asociar
  const [email, setEmail] = useState("")
  const [role, setRole] = useState<RolComercio>("cashier")
  const [asociando, setAsociando] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [formSuccess, setFormSuccess] = useState<string | null>(null)

  async function cargarEmpleados() {
    try {
      const data = await api.empleados.listar(comercioId)
      setEmpleados(data)
    } catch {
      setError("No se pudieron cargar los empleados")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    cargarEmpleados()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [comercioId])

  async function handleAsociar(e: React.FormEvent) {
    e.preventDefault()
    setFormError(null)
    setFormSuccess(null)
    setAsociando(true)
    try {
      const nuevo = await api.empleados.asociar(comercioId, { email, role })
      setEmpleados((prev) => {
        const idx = prev.findIndex((e) => e.user_id === nuevo.user_id)
        if (idx >= 0) {
          const updated = [...prev]
          updated[idx] = nuevo
          return updated
        }
        return [...prev, nuevo]
      })
      setEmail("")
      setRole("cashier")
      setFormSuccess(`${nuevo.name} fue asociado como ${ROLE_LABELS[nuevo.role]}.`)
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Error al asociar el empleado")
    } finally {
      setAsociando(false)
    }
  }

  async function handleCambiarRol(userId: string, nuevoRol: RolComercio) {
    try {
      const actualizado = await api.empleados.cambiarRol(comercioId, userId, nuevoRol)
      setEmpleados((prev) => prev.map((e) => (e.user_id === actualizado.user_id ? actualizado : e)))
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Error al cambiar el rol")
    }
  }

  async function handleDarDeBaja(userId: string, nombre: string) {
    if (!confirm(`¿Dar de baja a ${nombre}?`)) return
    try {
      await api.empleados.darDeBaja(comercioId, userId)
      setEmpleados((prev) => prev.filter((e) => e.user_id !== userId))
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Error al dar de baja")
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="font-serif text-3xl text-brown mb-1">Empleados</h1>
        <p className="text-brown-muted text-sm">Gestioná los miembros de tu comercio y sus roles.</p>
      </div>

      {/* Formulario de asociar */}
      <div className="card p-6">
        <h2 className="font-semibold text-brown mb-4 flex items-center gap-2">
          <UserPlus className="w-4 h-4" />
          Asociar empleado
        </h2>
        <form onSubmit={handleAsociar} className="flex flex-col sm:flex-row gap-3">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="correo@ejemplo.com"
            data-testid="input-email"
            className="flex-1 border border-border rounded-xl px-4 py-2.5 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand transition-colors"
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as RolComercio)}
            data-testid="select-rol"
            className="border border-border rounded-xl px-3 py-2.5 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand transition-colors"
          >
            {ROLES_ASIGNABLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABELS[r]}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={asociando}
            data-testid="btn-asociar"
            className="btn-primary px-5 py-2.5 text-sm disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {asociando ? "Asociando..." : "Asociar"}
          </button>
        </form>

        {formError && (
          <p role="alert" className="text-red-600 text-sm mt-3 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {formError}
          </p>
        )}
        {formSuccess && (
          <p className="text-green-700 text-sm mt-3 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
            {formSuccess}
          </p>
        )}
      </div>

      {/* Lista de empleados */}
      <div className="card p-6">
        <h2 className="font-semibold text-brown mb-4">Miembros actuales</h2>

        {loading && (
          <p className="text-brown-muted text-sm text-center py-6" data-testid="loading">
            Cargando...
          </p>
        )}

        {error && (
          <p role="alert" className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        {!loading && !error && (
          <ul className="divide-y divide-border" data-testid="lista-empleados">
            {empleados.map((emp) => (
              <li key={emp.user_id} className="py-3 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium text-brown text-sm truncate">{emp.name}</p>
                  <p className="text-brown-muted text-xs truncate">{emp.email}</p>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {emp.role === "owner" ? (
                    <span className="text-xs font-medium text-brand bg-brand-pale px-2.5 py-1 rounded-full">
                      {ROLE_LABELS[emp.role]}
                    </span>
                  ) : (
                    <>
                      <select
                        value={emp.role}
                        onChange={(e) => handleCambiarRol(emp.user_id, e.target.value as RolComercio)}
                        aria-label={`Rol de ${emp.name}`}
                        className="border border-border rounded-lg px-2 py-1 text-xs text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30"
                      >
                        {ROLES_ASIGNABLES.map((r) => (
                          <option key={r} value={r}>
                            {ROLE_LABELS[r]}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={() => handleDarDeBaja(emp.user_id, emp.name)}
                        aria-label={`Dar de baja a ${emp.name}`}
                        className="p-1.5 rounded-lg text-brown-muted hover:text-red-600 hover:bg-red-50 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
