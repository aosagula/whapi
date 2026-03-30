"use client"

/**
 * Selector de comercios post-login.
 * Lista los comercios del usuario. Si no tiene ninguno, muestra mensaje informativo.
 */
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Store, ChevronRight, LogOut, Plus } from "lucide-react"
import { api, ApiError, type ComercioResponse, type UserResponse } from "@/lib/api"

const ROLE_LABELS: Record<string, string> = {
  owner: "Dueño",
  admin: "Administrador",
  cashier: "Cajero",
  cook: "Cocinero",
  delivery: "Repartidor",
}

export default function SelectorPage() {
  const router = useRouter()
  const [comercios, setComercios] = useState<ComercioResponse[]>([])
  const [user, setUser] = useState<UserResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api.comercios.misComercio(), api.auth.me()])
      .then(([res, me]) => {
        setComercios(res.comercios)
        setUser(me)
      })
      .catch((err) => {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          // Sin autenticar → redirigir al login
          router.replace("/login")
        } else {
          setError("No se pudieron cargar tus comercios")
        }
      })
      .finally(() => setLoading(false))
  }, [router])

  function handleSelect(comercio: ComercioResponse) {
    // Guardar el comercio activo en localStorage para el panel
    localStorage.setItem("comercio_id", comercio.id)
    localStorage.setItem("comercio_name", comercio.name)
    localStorage.setItem("comercio_role", comercio.role)
    router.push(`/${comercio.id}/pedidos`)
  }

  function handleLogout() {
    localStorage.removeItem("access_token")
    localStorage.removeItem("comercio_id")
    localStorage.removeItem("comercio_name")
    document.cookie = "access_token=; path=/; max-age=0"
    router.replace("/login")
  }

  return (
    <div className="min-h-screen bg-hero-warm flex flex-col items-center justify-center px-4 py-12">
      {/* Logo */}
      <span className="font-serif text-3xl text-brown mb-10">Whapi</span>

      <div className="w-full max-w-lg">
        <div className="card p-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="font-serif text-2xl text-brown" data-testid="selector-title">
                Tus comercios
              </h1>
              <p className="text-brown-muted text-sm mt-1">Seleccioná el comercio con el que querés trabajar</p>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 text-sm text-brown-muted hover:text-brand transition-colors"
              title="Cerrar sesión"
            >
              <LogOut className="w-4 h-4" />
              Salir
            </button>
          </div>

          {loading && (
            <div className="py-12 text-center text-brown-muted text-sm" data-testid="loading">
              Cargando...
            </div>
          )}

          {error && (
            <p role="alert" className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-3 text-center">
              {error}
            </p>
          )}

          {!loading && !error && comercios.length === 0 && (
            <div className="py-10 text-center" data-testid="sin-comercios">
              <div className="w-16 h-16 rounded-2xl bg-brand-pale flex items-center justify-center mx-auto mb-4">
                <Store className="w-8 h-8 text-brand" />
              </div>
              <p className="font-semibold text-brown mb-2">Todavía no tenés comercios</p>
              {user?.account_type === "owner" ? (
                <>
                  <p className="text-brown-muted text-sm max-w-xs mx-auto mb-5">
                    Creá tu primer comercio para empezar a gestionar pedidos por WhatsApp.
                  </p>
                  <button
                    onClick={() => router.push("/nuevo-comercio")}
                    data-testid="btn-crear-comercio"
                    className="btn-primary inline-flex items-center gap-2 px-5 py-2.5 text-sm"
                  >
                    <Plus className="w-4 h-4" />
                    Crear mi comercio
                  </button>
                </>
              ) : (
                <p className="text-brown-muted text-sm max-w-xs mx-auto">
                  Esperá a que el dueño de un comercio te asocie para poder acceder al panel.
                </p>
              )}
            </div>
          )}

          {!loading && comercios.length > 0 && user?.account_type === "owner" && (
            <div className="mb-4 flex justify-end">
              <button
                onClick={() => router.push("/nuevo-comercio")}
                data-testid="btn-nuevo-comercio"
                className="inline-flex items-center gap-1.5 text-sm text-brand font-medium hover:underline"
              >
                <Plus className="w-3.5 h-3.5" />
                Nuevo comercio
              </button>
            </div>
          )}

          {!loading && comercios.length > 0 && (
            <ul className="space-y-3" data-testid="lista-comercios">
              {comercios.map((comercio) => (
                <li key={comercio.id}>
                  <button
                    onClick={() => handleSelect(comercio)}
                    className="w-full text-left border-2 border-border rounded-2xl p-4 hover:border-brand hover:bg-brand-pale transition-all group flex items-center justify-between"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-11 h-11 rounded-xl bg-brand-pale group-hover:bg-brand/20 flex items-center justify-center transition-colors flex-shrink-0">
                        <Store className="w-5 h-5 text-brand" />
                      </div>
                      <div>
                        <p className="font-semibold text-brown text-sm">{comercio.name}</p>
                        <p className="text-brown-muted text-xs mt-0.5">
                          {ROLE_LABELS[comercio.role] ?? comercio.role}
                          {comercio.address ? ` · ${comercio.address}` : ""}
                        </p>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-brown-muted group-hover:text-brand transition-colors flex-shrink-0" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
