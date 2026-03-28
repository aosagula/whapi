/**
 * Tests de la página de roles y permisos.
 */
import { render, screen } from "@testing-library/react"
import { useParams } from "next/navigation"
import PermisosPage from "@/app/[comercio_id]/ajustes/permisos/page"

jest.mock("next/navigation", () => ({
  useParams: jest.fn(),
}))

// Link de Next.js requiere mock básico en Jest
jest.mock("next/link", () => {
  return function MockLink({ href, children }: { href: string; children: React.ReactNode }) {
    return <a href={href}>{children}</a>
  }
})

describe("PermisosPage", () => {
  beforeEach(() => {
    ;(useParams as jest.Mock).mockReturnValue({ comercio_id: "cid-1" })
  })

  it("muestra la lista de roles", () => {
    render(<PermisosPage />)
    expect(screen.getByTestId("lista-roles")).toBeInTheDocument()
  })

  it("muestra los 5 roles del sistema", () => {
    render(<PermisosPage />)
    expect(screen.getByText("Dueño")).toBeInTheDocument()
    expect(screen.getByText("Administrador")).toBeInTheDocument()
    expect(screen.getByText("Cajero")).toBeInTheDocument()
    expect(screen.getByText("Cocinero")).toBeInTheDocument()
    expect(screen.getByText("Repartidor")).toBeInTheDocument()
  })

  it("muestra el título de la página", () => {
    render(<PermisosPage />)
    expect(screen.getByText("Roles y permisos")).toBeInTheDocument()
  })
})
