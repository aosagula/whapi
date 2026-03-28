"use client"

/**
 * Selector de comercio activo en el sidebar.
 * Expandido: nombre + icono de cambio. Minimizado: solo icono de tienda.
 * Al hacer clic → redirige al selector de comercios.
 */
import { useRouter } from "next/navigation"
import { Store, ChevronsUpDown } from "lucide-react"

interface ComercioSwitcherProps {
  comercioName: string
  collapsed: boolean
}

export default function ComercioSwitcher({ comercioName, collapsed }: ComercioSwitcherProps) {
  const router = useRouter()

  return (
    <button
      onClick={() => router.push("/selector")}
      data-testid="comercio-switcher"
      title={collapsed ? comercioName : undefined}
      className={`flex items-center gap-3 mx-2 mb-3 px-3 py-2 rounded-xl border border-border hover:border-brand hover:bg-brand-pale transition-all group ${
        collapsed ? "justify-center" : ""
      }`}
    >
      <Store className="w-4 h-4 text-brand flex-shrink-0" />
      {!collapsed && (
        <>
          <span className="text-sm font-semibold text-brown truncate flex-1 text-left">{comercioName}</span>
          <ChevronsUpDown className="w-3.5 h-3.5 text-brown-muted group-hover:text-brand transition-colors flex-shrink-0" />
        </>
      )}
    </button>
  )
}
