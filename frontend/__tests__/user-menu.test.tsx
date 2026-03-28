/**
 * Tests del menú de usuario del sidebar.
 */
import { render, screen, fireEvent } from "@testing-library/react"
import { useRouter } from "next/navigation"
import UserMenu from "@/components/layout/UserMenu"

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
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

describe("UserMenu", () => {
  const mockReplace = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useRouter as jest.Mock).mockReturnValue({ replace: mockReplace })
    Object.defineProperty(window, "localStorage", {
      value: { removeItem: jest.fn() },
      writable: true,
    })
    Object.defineProperty(document, "cookie", {
      writable: true,
      value: "",
    })
  })

  it("muestra el botón de usuario", () => {
    render(<UserMenu comercioId="cid-1" collapsed={false} userName="Carlos López" />)
    expect(screen.getByTestId("btn-user-menu")).toBeInTheDocument()
  })

  it("muestra el nombre del usuario en modo expandido", () => {
    render(<UserMenu comercioId="cid-1" collapsed={false} userName="Carlos López" />)
    expect(screen.getByText("Carlos López")).toBeInTheDocument()
  })

  it("no muestra el nombre en modo colapsado", () => {
    render(<UserMenu comercioId="cid-1" collapsed={true} userName="Carlos López" />)
    expect(screen.queryByText("Carlos López")).not.toBeInTheDocument()
  })

  it("abre el dropdown al hacer clic", () => {
    render(<UserMenu comercioId="cid-1" collapsed={false} userName="Carlos" />)
    expect(screen.queryByTestId("user-menu-dropdown")).not.toBeInTheDocument()
    fireEvent.click(screen.getByTestId("btn-user-menu"))
    expect(screen.getByTestId("user-menu-dropdown")).toBeInTheDocument()
  })

  it("muestra opciones de editar perfil y cerrar sesión", () => {
    render(<UserMenu comercioId="cid-1" collapsed={false} userName="Carlos" />)
    fireEvent.click(screen.getByTestId("btn-user-menu"))
    expect(screen.getByTestId("menu-editar-perfil")).toBeInTheDocument()
    expect(screen.getByTestId("menu-cerrar-sesion")).toBeInTheDocument()
  })

  it("redirige al login al cerrar sesión", () => {
    render(<UserMenu comercioId="cid-1" collapsed={false} userName="Carlos" />)
    fireEvent.click(screen.getByTestId("btn-user-menu"))
    fireEvent.click(screen.getByTestId("menu-cerrar-sesion"))
    expect(mockReplace).toHaveBeenCalledWith("/login")
  })

  it("las iniciales del avatar se calculan correctamente", () => {
    render(<UserMenu comercioId="cid-1" collapsed={false} userName="Ana García" />)
    expect(screen.getByText("AG")).toBeInTheDocument()
  })
})
