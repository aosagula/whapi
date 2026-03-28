"use client"

/**
 * Página de registro bifurcado.
 * Paso 1: elige tipo de cuenta (dueño / empleado).
 * Paso 2: completa datos personales.
 */
import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Store, Users } from "lucide-react"
import { api, ApiError } from "@/lib/api"

type AccountType = "owner" | "employee"
type Step = "tipo" | "datos"

export default function RegistroPage() {
  const router = useRouter()
  const [step, setStep] = useState<Step>("tipo")
  const [accountType, setAccountType] = useState<AccountType | null>(null)

  // Campos del formulario
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [phone, setPhone] = useState("")

  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  function handleSelectType(type: AccountType) {
    setAccountType(type)
    setStep("datos")
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!accountType) return
    setError(null)
    setLoading(true)

    try {
      const data = await api.auth.registro({
        name,
        email,
        password,
        account_type: accountType,
        phone: phone || undefined,
      })

      // Auto-login: guardar token
      localStorage.setItem("access_token", data.token.access_token)
      document.cookie = `access_token=${data.token.access_token}; path=/; max-age=3600; SameSite=Lax`

      // Dueño → va al selector (donde se le ofrecerá crear su primer comercio en Fase 2)
      // Empleado → también va al selector (verá el mensaje de "sin comercios")
      router.push("/selector")
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("Ya existe una cuenta con ese email")
      } else if (err instanceof ApiError && err.status === 422) {
        setError("Verificá los datos ingresados. La contraseña debe tener al menos 8 caracteres.")
      } else {
        setError("Ocurrió un error. Intentá de nuevo.")
      }
    } finally {
      setLoading(false)
    }
  }

  // ── Paso 1: elegir tipo ─────────────────────────────────────────────────────
  if (step === "tipo") {
    return (
      <div className="card p-8">
        <h1 className="font-serif text-3xl text-brown mb-2">Crear cuenta</h1>
        <p className="text-brown-muted text-sm mb-8">¿Cómo vas a usar Whapi?</p>

        <div className="space-y-4">
          <button
            onClick={() => handleSelectType("owner")}
            className="w-full text-left border-2 border-border rounded-2xl p-5 hover:border-brand hover:bg-brand-pale transition-all group"
            data-testid="tipo-dueno"
          >
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-brand-pale group-hover:bg-brand/20 flex items-center justify-center flex-shrink-0 transition-colors">
                <Store className="w-6 h-6 text-brand" />
              </div>
              <div>
                <p className="font-semibold text-brown text-base">Soy dueño de un comercio</p>
                <p className="text-brown-muted text-sm mt-1">
                  Registrá tu cuenta y configurá tu pizzería para recibir pedidos por WhatsApp.
                </p>
              </div>
            </div>
          </button>

          <button
            onClick={() => handleSelectType("employee")}
            className="w-full text-left border-2 border-border rounded-2xl p-5 hover:border-brand hover:bg-brand-pale transition-all group"
            data-testid="tipo-empleado"
          >
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-brand-pale group-hover:bg-brand/20 flex items-center justify-center flex-shrink-0 transition-colors">
                <Users className="w-6 h-6 text-brand" />
              </div>
              <div>
                <p className="font-semibold text-brown text-base">Soy empleado / colaborador</p>
                <p className="text-brown-muted text-sm mt-1">
                  Creá tu cuenta y esperá a que el dueño te asocie a su comercio.
                </p>
              </div>
            </div>
          </button>
        </div>

        <p className="text-center text-sm text-brown-muted mt-8">
          ¿Ya tenés cuenta?{" "}
          <Link href="/login" className="text-brand font-semibold hover:underline">
            Iniciá sesión
          </Link>
        </p>
      </div>
    )
  }

  // ── Paso 2: datos personales ────────────────────────────────────────────────
  return (
    <div className="card p-8">
      <button
        onClick={() => setStep("tipo")}
        className="text-sm text-brown-muted hover:text-brand mb-4 flex items-center gap-1 transition-colors"
      >
        ← Volver
      </button>

      <h1 className="font-serif text-3xl text-brown mb-1">
        {accountType === "owner" ? "Registrá tu cuenta" : "Crear cuenta"}
      </h1>
      <p className="text-brown-muted text-sm mb-8">
        {accountType === "owner"
          ? "Completá tus datos para empezar a configurar tu comercio."
          : "Completá tus datos para crear tu cuenta."}
      </p>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-semibold text-brown mb-1.5" htmlFor="name">
            Nombre completo
          </label>
          <input
            id="name"
            type="text"
            required
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full border border-border rounded-xl px-4 py-3 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand transition-colors"
            placeholder="Juan Pérez"
          />
        </div>

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
          <label className="block text-sm font-semibold text-brown mb-1.5" htmlFor="phone">
            Teléfono{" "}
            <span className="font-normal text-brown-muted">(opcional)</span>
          </label>
          <input
            id="phone"
            type="tel"
            autoComplete="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="w-full border border-border rounded-xl px-4 py-3 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand transition-colors"
            placeholder="+54 11 1234-5678"
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
            autoComplete="new-password"
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full border border-border rounded-xl px-4 py-3 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand transition-colors"
            placeholder="Mínimo 8 caracteres"
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
          {loading ? "Creando cuenta..." : "Crear cuenta"}
        </button>
      </form>

      <p className="text-center text-sm text-brown-muted mt-6">
        ¿Ya tenés cuenta?{" "}
        <Link href="/login" className="text-brand font-semibold hover:underline">
          Iniciá sesión
        </Link>
      </p>
    </div>
  )
}
