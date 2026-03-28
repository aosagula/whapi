"use client"

/**
 * Menú de usuario en la esquina inferior izquierda del sidebar.
 * Expandido: avatar + nombre + dropdown con opciones.
 * Minimizado: solo avatar con tooltip.
 */
import { useState, useRef, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { UserCircle, LogOut, UserCog } from "lucide-react"

interface UserMenuProps {
  comercioId: string
  collapsed: boolean
  userName: string
}

export default function UserMenu({ comercioId, collapsed, userName }: UserMenuProps) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Cerrar al hacer clic fuera
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
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

  const initials = userName
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("")

  return (
    <div ref={ref} className="relative px-2 pb-4 mt-2">
      <button
        onClick={() => setOpen((o) => !o)}
        data-testid="btn-user-menu"
        aria-label="Menú de usuario"
        className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-[#f5f0e8] transition-colors ${
          collapsed ? "justify-center" : ""
        }`}
      >
        {/* Avatar */}
        <div className="w-7 h-7 rounded-full bg-brand text-white flex items-center justify-center text-xs font-bold flex-shrink-0">
          {initials || <UserCircle className="w-4 h-4" />}
        </div>
        {!collapsed && (
          <span className="text-sm font-medium text-brown truncate text-left flex-1">{userName}</span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div
          data-testid="user-menu-dropdown"
          className={`absolute bottom-full mb-1 bg-white border border-border rounded-xl shadow-lg py-1.5 z-50 min-w-[180px] ${
            collapsed ? "left-full ml-3 bottom-0" : "left-2 right-2"
          }`}
        >
          <Link
            href={`/${comercioId}/perfil`}
            onClick={() => setOpen(false)}
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
  )
}
