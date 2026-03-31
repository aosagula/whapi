"use client"

/**
 * Sidebar colapsable del panel operativo.
 * Expandido: icono + texto. Minimizado: solo icono con tooltip al hacer hover.
 * Submenú de Ajustes expandible (acordeón).
 */
import { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  ShoppingBag,
  Phone,
  Users,
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
} from "lucide-react"

interface SidebarProps {
  comercioId: string
}

interface NavItem {
  href: string
  label: string
  icon: React.ElementType
  children?: NavItem[]
}

function buildNav(comercioId: string): NavItem[] {
  const base = `/${comercioId}`
  return [
    { href: `${base}/pedidos`, label: "Pedidos", icon: ShoppingBag },
    { href: `${base}/pedidos-manuales`, label: "Pedidos manuales", icon: Phone },
    { href: `${base}/clientes`, label: "Clientes", icon: Users },
    {
      href: `${base}/ajustes`,
      label: "Ajustes",
      icon: Settings,
      children: [
        { href: `${base}/ajustes/permisos`, label: "Permisos", icon: Lock },
        { href: `${base}/ajustes/empleados`, label: "Empleados", icon: UserCheck },
        { href: `${base}/ajustes/productos`, label: "Productos", icon: Pizza },
        { href: `${base}/ajustes/combos`, label: "Combos", icon: Gift },
        { href: `${base}/ajustes/whatsapp`, label: "WhatsApp", icon: Smartphone },
      ],
    },
    { href: `${base}/reportes`, label: "Reportes", icon: BarChart2 },
  ]
}

interface TooltipProps {
  label: string
  children: React.ReactNode
}

function Tooltip({ label, children }: TooltipProps) {
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

export default function Sidebar({ comercioId }: SidebarProps) {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)
  const [ajustesOpen, setAjustesOpen] = useState(
    pathname.includes("/ajustes")
  )
  const nav = buildNav(comercioId)

  function isActive(href: string) {
    return pathname === href || (href !== `/${comercioId}` && pathname.startsWith(href))
  }

  return (
    <aside
      data-testid="sidebar"
      data-collapsed={collapsed}
      className={`relative flex flex-col bg-white border-r border-border transition-all duration-200 ${
        collapsed ? "w-16" : "w-56"
      }`}
    >
      {/* Logo / marca */}
      <div className={`px-4 pt-5 pb-4 flex items-center ${collapsed ? "justify-center" : "justify-between"}`}>
        {!collapsed && (
          <span className="font-serif text-xl text-brown leading-none">Whapi</span>
        )}
        <button
          onClick={() => setCollapsed((c) => !c)}
          data-testid="btn-toggle-sidebar"
          aria-label={collapsed ? "Expandir menú" : "Minimizar menú"}
          className="p-1 rounded-lg text-brown-muted hover:text-brand hover:bg-brand-pale transition-colors"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Navegación */}
      <nav className="flex-1 px-2 space-y-0.5 overflow-y-auto">
        {nav.map((item) => {
          if (item.children) {
            const active = isActive(item.href)
            return (
              <div key={item.href}>
                {collapsed ? (
                  <Tooltip label={item.label}>
                    <button
                      onClick={() => {
                        setCollapsed(false)
                        setAjustesOpen(true)
                      }}
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
                      data-testid="btn-toggle-ajustes"
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
                            data-testid={`nav-${child.href.split("/").pop()}`}
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
                    data-testid={`nav-${item.href.split("/").pop()}`}
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
                  data-testid={`nav-${item.href.split("/").pop()}`}
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
    </aside>
  )
}
