/**
 * Tests del Sidebar de navegación.
 */
import { render, screen, fireEvent } from "@testing-library/react"
import { usePathname } from "next/navigation"
import Sidebar from "@/components/layout/Sidebar"

jest.mock("next/navigation", () => ({
  usePathname: jest.fn(),
}))

jest.mock("next/link", () => {
  return function MockLink({
    href,
    children,
    ...props
  }: {
    href: string
    children: React.ReactNode
    [key: string]: unknown
  }) {
    return <a href={href} {...props}>{children}</a>
  }
})

const CID = "cid-test"

describe("Sidebar", () => {
  beforeEach(() => {
    ;(usePathname as jest.Mock).mockReturnValue(`/${CID}/pedidos`)
  })

  it("se renderiza en modo expandido por defecto", () => {
    render(<Sidebar comercioId={CID} />)
    const sidebar = screen.getByTestId("sidebar")
    expect(sidebar.dataset.collapsed).toBe("false")
  })

  it("se colapsa al hacer clic en el botón de toggle", () => {
    render(<Sidebar comercioId={CID} />)
    fireEvent.click(screen.getByTestId("btn-toggle-sidebar"))
    const sidebar = screen.getByTestId("sidebar")
    expect(sidebar.dataset.collapsed).toBe("true")
  })

  it("se expande nuevamente al hacer clic de nuevo", () => {
    render(<Sidebar comercioId={CID} />)
    const btn = screen.getByTestId("btn-toggle-sidebar")
    fireEvent.click(btn)
    fireEvent.click(btn)
    const sidebar = screen.getByTestId("sidebar")
    expect(sidebar.dataset.collapsed).toBe("false")
  })

  it("muestra los ítems de navegación principales", () => {
    render(<Sidebar comercioId={CID} />)
    expect(screen.getByText("Pedidos")).toBeInTheDocument()
    expect(screen.getByText("Pedidos manuales")).toBeInTheDocument()
    expect(screen.getByText("Clientes")).toBeInTheDocument()
    expect(screen.getByText("Reportes")).toBeInTheDocument()
  })

  it("muestra el submenú de Ajustes cuando la ruta incluye /ajustes", () => {
    ;(usePathname as jest.Mock).mockReturnValue(`/${CID}/ajustes/empleados`)
    render(<Sidebar comercioId={CID} />)
    expect(screen.getByText("Empleados")).toBeInTheDocument()
    expect(screen.getByText("Permisos")).toBeInTheDocument()
    expect(screen.getByText("Productos")).toBeInTheDocument()
    expect(screen.getByText("Combos")).toBeInTheDocument()
  })

  it("expande el submenú de Ajustes al hacer clic en Ajustes", () => {
    render(<Sidebar comercioId={CID} />)
    // El submenú no está visible inicialmente (ruta en /pedidos)
    expect(screen.queryByText("Empleados")).not.toBeInTheDocument()
    // Hacer clic en el botón de Ajustes
    fireEvent.click(screen.getByTestId("btn-toggle-ajustes"))
    expect(screen.getByText("Empleados")).toBeInTheDocument()
  })

  it("los links tienen el href correcto", () => {
    render(<Sidebar comercioId={CID} />)
    const pedidosLink = screen.getByTestId("nav-pedidos")
    expect(pedidosLink).toHaveAttribute("href", `/${CID}/pedidos`)
  })

  it("el botón toggle tiene el aria-label correcto", () => {
    render(<Sidebar comercioId={CID} />)
    expect(screen.getByLabelText("Minimizar menú")).toBeInTheDocument()
    fireEvent.click(screen.getByTestId("btn-toggle-sidebar"))
    expect(screen.getByLabelText("Expandir menú")).toBeInTheDocument()
  })
})
