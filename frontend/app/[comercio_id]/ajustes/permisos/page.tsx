"use client"

/**
 * Referencia de roles y permisos del comercio.
 * Vista informativa, sin modificaciones.
 */
import Link from "next/link"
import { useParams } from "next/navigation"
import { ChevronLeft } from "lucide-react"

const ROLES = [
  {
    name: "Dueño",
    key: "owner",
    description: "Acceso total. Puede gestionar empleados, catálogo, pedidos y configuración del comercio.",
    permisos: ["Ver y operar pedidos", "Gestionar empleados y roles", "Editar catálogo", "Configurar comercio"],
  },
  {
    name: "Administrador",
    key: "admin",
    description: "Igual que el dueño excepto que no puede modificar al dueño ni la configuración crítica del comercio.",
    permisos: ["Ver y operar pedidos", "Gestionar empleados y roles", "Editar catálogo"],
  },
  {
    name: "Cajero",
    key: "cashier",
    description: "Atiende pedidos telefónicos y conversaciones de WhatsApp derivadas.",
    permisos: ["Ver y operar pedidos", "Atender conversaciones HITL", "Cargar pedido manual"],
  },
  {
    name: "Cocinero",
    key: "cook",
    description: "Visualiza el tablero de producción y confirma pedidos listos.",
    permisos: ["Ver pedidos en producción", "Marcar pedido como listo"],
  },
  {
    name: "Repartidor",
    key: "delivery",
    description: "Visualiza los pedidos asignados y actualiza el estado de entrega.",
    permisos: ["Ver pedidos para entregar", "Marcar pedido como entregado"],
  },
]

export default function PermisosPage() {
  const params = useParams()
  const comercioId = params.comercio_id as string

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <Link
          href={`/${comercioId}/ajustes/empleados`}
          className="inline-flex items-center gap-1 text-sm text-brown-muted hover:text-brand transition-colors mb-4"
        >
          <ChevronLeft className="w-4 h-4" />
          Empleados
        </Link>
        <h1 className="font-serif text-3xl text-brown mb-1">Roles y permisos</h1>
        <p className="text-brown-muted text-sm">Referencia de lo que puede hacer cada rol en el comercio.</p>
      </div>

      <div className="space-y-4" data-testid="lista-roles">
        {ROLES.map((rol) => (
          <div key={rol.key} className="card p-5">
            <h2 className="font-semibold text-brown mb-1">{rol.name}</h2>
            <p className="text-brown-muted text-sm mb-3">{rol.description}</p>
            <ul className="space-y-1">
              {rol.permisos.map((permiso) => (
                <li key={permiso} className="flex items-center gap-2 text-sm text-brown">
                  <span className="w-1.5 h-1.5 rounded-full bg-brand flex-shrink-0" />
                  {permiso}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}
