import Link from "next/link"
import {
  MessageCircle,
  LayoutDashboard,
  Zap,
  Users,
  BarChart3,
  ChevronRight,
  CheckCircle2,
} from "lucide-react"

// Características principales de la plataforma
const features = [
  {
    icon: MessageCircle,
    title: "Chatbot con IA",
    description:
      "Un asistente conversacional que toma pedidos por WhatsApp de forma natural, sin menús rígidos ni opciones numeradas.",
  },
  {
    icon: LayoutDashboard,
    title: "Panel en tiempo real",
    description:
      "Tablero Kanban para gestionar pedidos por estado. Tu equipo ve todo lo que pasa en la pizzería al instante.",
  },
  {
    icon: Zap,
    title: "Pagos automáticos",
    description:
      "Integración con MercadoPago. El bot envía el link, el pago se confirma y el pedido avanza solo.",
  },
  {
    icon: Users,
    title: "Multi-sucursal",
    description:
      "Gestioná varias pizzerías desde una sola cuenta. Cada una con su equipo, menú y números de WhatsApp.",
  },
  {
    icon: BarChart3,
    title: "Reportes y métricas",
    description:
      "Ventas, cancelaciones, métodos de pago e incidencias. Reportes por sucursal y consolidados.",
  },
  {
    icon: CheckCircle2,
    title: "Operador humano (HITL)",
    description:
      "Cuando el bot no puede resolver, deriva al cajero. El operador atiende desde el panel sin perder el contexto.",
  },
]

// Pasos del onboarding para el dueño
const steps = [
  { number: "01", title: "Registrá tu cuenta", description: "Creá tu cuenta y da de alta tu primera pizzería en minutos." },
  { number: "02", title: "Conectá WhatsApp", description: "Escaneá el QR y vinculá tu número. Podés agregar más después." },
  { number: "03", title: "Cargá tu menú", description: "Agregá pizzas, empanadas, bebidas y combos con precios y fotos." },
  { number: "04", title: "Empezá a recibir pedidos", description: "El chatbot atiende solo. Tu equipo gestiona desde el panel." },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-cream">
      {/* ── Navbar ─────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 bg-cream/90 backdrop-blur-sm border-b border-border">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <span className="font-serif text-2xl text-brown font-normal">Whapi</span>
          <div className="flex items-center gap-3">
            <Link href="/login">
              <button className="btn-outline py-2 px-5 text-sm">Iniciar sesión</button>
            </Link>
            <Link href="/registro">
              <button className="btn-primary py-2 px-5 text-sm">Registrarse</button>
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero + Video ───────────────────────────────────── */}
      <section
        className="relative overflow-hidden"
        style={{ background: "linear-gradient(160deg, #fff8f0 0%, #ffe8d2 100%)" }}
        data-testid="hero"
      >
        {/* Blur decorativo */}
        <div
          className="absolute pointer-events-none"
          style={{
            width: 600,
            height: 600,
            background: "radial-gradient(circle, rgba(232,93,4,.12) 0%, transparent 70%)",
            top: -100,
            right: -100,
          }}
        />
        <div className="max-w-6xl mx-auto px-6 py-20 md:py-28 relative">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            {/* Columna izquierda: texto */}
            <div>
              <div className="inline-flex items-center gap-2 bg-brand-pale border border-brand/20 text-brand text-sm font-semibold px-4 py-2 rounded-full mb-8">
                <span className="w-2 h-2 rounded-full bg-brand animate-pulse" />
                Plataforma multi-tenant para comercios gastronómicos
              </div>

              <h1 className="font-serif text-5xl md:text-6xl text-brown leading-tight mb-6">
                Pedidos por WhatsApp,{" "}
                <span className="text-brand italic">sin complicaciones</span>
              </h1>

              <p className="text-brown-mid text-lg md:text-xl mb-10 leading-relaxed">
                Tu pizzería recibe y gestiona pedidos automáticamente por WhatsApp. Un chatbot con IA
                atiende a tus clientes 24/7 y tu equipo lo controla todo desde un panel en tiempo real.
              </p>

              <div className="flex flex-col sm:flex-row items-start gap-4">
                <Link href="/registro">
                  <button className="btn-primary text-base px-8 py-4 flex items-center gap-2">
                    Empezar gratis
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </Link>
                <Link href="/login">
                  <button className="btn-outline text-base px-8 py-4">Iniciar sesión</button>
                </Link>
              </div>
            </div>

            {/* Columna derecha: video */}
            <div className="rounded-2xl overflow-hidden shadow-2xl border border-brand/10">
              <video
                src="/whapi.mp4"
                autoPlay
                loop
                muted
                playsInline
                className="w-full"
              />
            </div>
          </div>
        </div>
      </section>

      {/* ── Características ────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="font-serif text-4xl md:text-5xl text-brown mb-4">
            Todo lo que necesitás
          </h2>
          <p className="text-brown-mid text-lg max-w-xl mx-auto">
            Desde el chatbot hasta los reportes, Whapi cubre todo el flujo operativo de tu pizzería.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature) => {
            const Icon = feature.icon
            return (
              <div key={feature.title} className="card p-6 hover:shadow-md transition-shadow">
                <div className="w-12 h-12 rounded-xl bg-brand-pale flex items-center justify-center mb-4">
                  <Icon className="w-6 h-6 text-brand" />
                </div>
                <h3 className="font-serif text-xl text-brown mb-2">{feature.title}</h3>
                <p className="text-brown-muted text-sm leading-relaxed">{feature.description}</p>
              </div>
            )
          })}
        </div>
      </section>

      {/* ── Cómo funciona ──────────────────────────────────── */}
      <section className="bg-brown py-24">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="font-serif text-4xl md:text-5xl text-cream mb-4">
              Arrancá en 4 pasos
            </h2>
            <p className="text-brand-light text-lg">Sin instalaciones complicadas ni técnicos.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {steps.map((step) => (
              <div key={step.number} className="text-center">
                <div className="text-brand font-serif text-5xl mb-4 opacity-60">{step.number}</div>
                <h3 className="font-serif text-xl text-cream mb-2">{step.title}</h3>
                <p className="text-brown-muted text-sm leading-relaxed">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA final ──────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 py-24 text-center">
        <h2 className="font-serif text-4xl md:text-5xl text-brown mb-6">
          ¿Listo para modernizar tu pizzería?
        </h2>
        <p className="text-brown-mid text-lg max-w-xl mx-auto mb-10">
          Registrá tu cuenta, conectá WhatsApp y empezá a recibir pedidos hoy mismo.
        </p>
        <Link href="/registro">
          <button className="btn-primary text-base px-10 py-4">
            Crear cuenta gratis
          </button>
        </Link>
      </section>

      {/* ── Footer ─────────────────────────────────────────── */}
      <footer className="border-t border-border py-8">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <span className="font-serif text-xl text-brown">Whapi</span>
          <p className="text-brown-muted text-sm">
            © {new Date().getFullYear()} Whapi. Plataforma de pedidos por WhatsApp.
          </p>
        </div>
      </footer>
    </div>
  )
}
