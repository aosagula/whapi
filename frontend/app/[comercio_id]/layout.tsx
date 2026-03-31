"use client"

/**
 * Layout del panel operativo del comercio.
 * Sidebar colapsable + contenido principal.
 */
import { useState, useEffect } from "react"
import { useParams, usePathname } from "next/navigation"
import {
  ShoppingBag,
  Phone,
  Users,
  MessageSquare,
  Settings,
  BarChart2,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Lock,
  UserCheck,
  Pizza,
  Gift,
  Smartphone,
  Store,
  ChevronsUpDown,
  UserCircle,
  LogOut,
  UserCog,
} from "lucide-react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { api } from "@/lib/api"

// ── Tipos ─────────────────────────────────────────────────────────────────────

interface NavItem {
  href: string
  label: string
  icon: React.ElementType
  testId?: string
  children?: NavItem[]
}

// ── Tooltip ───────────────────────────────────────────────────────────────────

function Tooltip({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="relative group/tip">
      {children}
      <div
        role="tooltip"
        className="absolute left-full ml-3 top-1/2 -translate-y-1/2 z-50
                   bg-brown text-cream text-xs font-medium px-2.5 py-1.5 rounded-lg
                   whitespace-nowrap pointer-events-none
                   opacity-0 group-hover/tip:opacity-100 transition-opacity duration-150"
      >
        {label}
      </div>
    </div>
  )
}

// ── Layout principal ──────────────────────────────────────────────────────────

export default function ComercioLayout({ children }: { children: React.ReactNode }) {
  const params = useParams()
  const pathname = usePathname()
  const router = useRouter()
  const comercioId = params.comercio_id as string

  const [collapsed, setCollapsed] = useState(false)
  const [ajustesOpen, setAjustesOpen] = useState(pathname.includes("/ajustes"))
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [userName, setUserName] = useState("")
  const [comercioName, setComercioName] = useState("Comercio")

  // Cargar datos desde localStorage y API
  useEffect(() => {
    const storedName = localStorage.getItem("comercio_name")
    if (storedName) setComercioName(storedName)

    api.auth.me().then((user) => setUserName(user.name)).catch(() => {})
  }, [])

  // Cerrar user menu al hacer clic fuera
  useEffect(() => {
    function handler(e: MouseEvent) {
      const menu = document.getElementById("user-menu-container")
      if (menu && !menu.contains(e.target as Node)) setUserMenuOpen(false)
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [])

  function handleLogout() {
    localStorage.removeItem("access_token")
    localStorage.removeItem("comercio_id")
    localStorage.removeItem("comercio_name")
    document.cookie = "access_token=; path=/; max-age=0"
    router.replace("/login")
  }

  const base = `/${comercioId}`
  const nav: NavItem[] = [
    { href: `${base}/pedidos`, label: "Pedidos", icon: ShoppingBag, testId: "nav-pedidos" },
    { href: `${base}/pedidos-manuales`, label: "Pedidos manuales", icon: Phone, testId: "nav-pedidos-manuales" },
    { href: `${base}/clientes`, label: "Clientes", icon: Users, testId: "nav-clientes" },
    { href: `${base}/conversaciones`, label: "Conversaciones", icon: MessageSquare, testId: "nav-conversaciones" },
    {
      href: `${base}/ajustes`,
      label: "Ajustes",
      icon: Settings,
      testId: "nav-ajustes",
      children: [
        { href: `${base}/ajustes/permisos`, label: "Permisos", icon: Lock, testId: "nav-permisos" },
        { href: `${base}/ajustes/empleados`, label: "Empleados", icon: UserCheck, testId: "nav-empleados" },
        { href: `${base}/ajustes/productos`, label: "Productos", icon: Pizza, testId: "nav-productos" },
        { href: `${base}/ajustes/combos`, label: "Combos", icon: Gift, testId: "nav-combos" },
        { href: `${base}/ajustes/whatsapp`, label: "WhatsApp", icon: Smartphone, testId: "nav-whatsapp" },
      ],
    },
    { href: `${base}/reportes`, label: "Reportes", icon: BarChart2, testId: "nav-reportes" },
  ]

  function isActive(href: string) {
    if (href === `${base}/ajustes`) return pathname.startsWith(`${base}/ajustes`)
    return pathname === href || pathname.startsWith(`${href}/`)
  }

  const initials = userName
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("")

  return (
    <div className="min-h-screen flex bg-[#faf7f2]">
      {/* ── Sidebar ─────────────────────────────────────────────── */}
      <aside
        data-testid="sidebar"
        data-collapsed={collapsed}
        className={`relative flex flex-col bg-white border-r border-border transition-all duration-200 ${
          collapsed ? "w-16" : "w-56"
        }`}
      >
        {/* Encabezado — logo + botón colapsar */}
        <div
          className={`px-3 pt-5 pb-3 flex items-center ${collapsed ? "justify-center" : "justify-between gap-2"}`}
        >
          {!collapsed && (
            <span className="font-serif text-xl text-brown leading-none px-1">Whapi</span>
          )}
          <button
            onClick={() => setCollapsed((c) => !c)}
            data-testid="btn-toggle-sidebar"
            aria-label={collapsed ? "Expandir menú" : "Minimizar menú"}
            className="p-1.5 rounded-lg text-brown-muted hover:text-brand hover:bg-brand-pale transition-colors flex-shrink-0"
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Switcher de comercio */}
        {collapsed ? (
          <Tooltip label={comercioName}>
            <button
              onClick={() => router.push("/selector")}
              data-testid="comercio-switcher"
              className="flex items-center justify-center mx-2 mb-3 p-2.5 rounded-xl border border-border hover:border-brand hover:bg-brand-pale transition-all"
            >
              <Store className="w-4 h-4 text-brand" />
            </button>
          </Tooltip>
        ) : (
          <button
            onClick={() => router.push("/selector")}
            data-testid="comercio-switcher"
            className="flex items-center gap-3 mx-2 mb-3 px-3 py-2 rounded-xl border border-border hover:border-brand hover:bg-brand-pale transition-all group"
          >
            <Store className="w-4 h-4 text-brand flex-shrink-0" />
            <span className="text-sm font-semibold text-brown truncate flex-1 text-left">{comercioName}</span>
            <ChevronsUpDown className="w-3.5 h-3.5 text-brown-muted group-hover:text-brand transition-colors flex-shrink-0" />
          </button>
        )}

        {/* Navegación principal */}
        <nav className="flex-1 px-2 space-y-0.5 overflow-y-auto">
          {nav.map((item) => {
            if (item.children) {
              const active = isActive(item.href)
              return (
                <div key={item.href}>
                  {collapsed ? (
                    <Tooltip label={item.label}>
                      <button
                        onClick={() => { setCollapsed(false); setAjustesOpen(true) }}
                        data-testid={item.testId}
                        className={`w-full flex items-center justify-center p-2.5 rounded-xl transition-colors ${
                          active ? "bg-brand-pale text-brand" : "text-brown-muted hover:text-brown hover:bg-[#f5f0e8]"
                        }`}
                      >
                        <item.icon className="w-5 h-5 flex-shrink-0" />
                      </button>
                    </Tooltip>
                  ) : (
                    <>
                      <button
                        onClick={() => setAjustesOpen((o) => !o)}
                        data-testid={item.testId ?? "btn-toggle-ajustes"}
                        className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
                          active ? "bg-brand-pale text-brand" : "text-brown-muted hover:text-brown hover:bg-[#f5f0e8]"
                        }`}
                      >
                        <item.icon className="w-4 h-4 flex-shrink-0" />
                        <span className="flex-1 text-left">{item.label}</span>
                        <ChevronDown
                          className={`w-3.5 h-3.5 transition-transform ${ajustesOpen ? "rotate-180" : ""}`}
                        />
                      </button>
                      {ajustesOpen && (
                        <div className="ml-4 mt-0.5 space-y-0.5 border-l border-border pl-3">
                          {item.children.map((child) => (
                            <Link
                              key={child.href}
                              href={child.href}
                              data-testid={child.testId}
                              className={`flex items-center gap-2.5 px-2 py-1.5 rounded-lg text-sm transition-colors ${
                                isActive(child.href)
                                  ? "text-brand font-medium"
                                  : "text-brown-muted hover:text-brown"
                              }`}
                            >
                              <child.icon className="w-3.5 h-3.5 flex-shrink-0" />
                              {child.label}
                            </Link>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )
            }

            return (
              <div key={item.href}>
                {collapsed ? (
                  <Tooltip label={item.label}>
                    <Link
                      href={item.href}
                      data-testid={item.testId}
                      className={`flex items-center justify-center p-2.5 rounded-xl transition-colors ${
                        isActive(item.href) ? "bg-brand-pale text-brand" : "text-brown-muted hover:text-brown hover:bg-[#f5f0e8]"
                      }`}
                    >
                      <item.icon className="w-5 h-5 flex-shrink-0" />
                    </Link>
                  </Tooltip>
                ) : (
                  <Link
                    href={item.href}
                    data-testid={item.testId}
                    className={`flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
                      isActive(item.href) ? "bg-brand-pale text-brand" : "text-brown-muted hover:text-brown hover:bg-[#f5f0e8]"
                    }`}
                  >
                    <item.icon className="w-4 h-4 flex-shrink-0" />
                    {item.label}
                  </Link>
                )}
              </div>
            )
          })}
        </nav>

        {/* ── Menú de usuario (inferior) ─────────────────────────── */}
        <div id="user-menu-container" className="relative px-2 pb-4 mt-2">
          <button
            onClick={() => setUserMenuOpen((o) => !o)}
            data-testid="btn-user-menu"
            aria-label="Menú de usuario"
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-[#f5f0e8] transition-colors ${
              collapsed ? "justify-center" : ""
            }`}
          >
            <div className="w-7 h-7 rounded-full bg-brand text-white flex items-center justify-center text-xs font-bold flex-shrink-0">
              {initials || <UserCircle className="w-4 h-4" />}
            </div>
            {!collapsed && (
              <span className="text-sm font-medium text-brown truncate text-left flex-1">{userName || "…"}</span>
            )}
          </button>

          {userMenuOpen && (
            <div
              data-testid="user-menu-dropdown"
              className={`absolute bottom-full mb-1 bg-white border border-border rounded-xl shadow-lg py-1.5 z-50 min-w-[180px] ${
                collapsed ? "left-full ml-3 bottom-0" : "left-2 right-2"
              }`}
            >
              <Link
                href={`/${comercioId}/perfil`}
                onClick={() => setUserMenuOpen(false)}
                data-testid="menu-editar-perfil"
                className="flex items-center gap-2.5 px-4 py-2 text-sm text-brown hover:bg-brand-pale transition-colors"
              >
                <UserCog className="w-4 h-4 text-brown-muted" />
                Editar perfil
              </Link>
              <div className="border-t border-border my-1" />
              <button
                onClick={handleLogout}
                data-testid="menu-cerrar-sesion"
                className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Cerrar sesión
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* ── Contenido principal ──────────────────────────────────── */}
      <main className="flex-1 overflow-auto p-8">{children}</main>
    </div>
  )
}
