/**
 * Tests del selector de comercios.
 */
import { render, screen, waitFor } from "@testing-library/react"
import { useRouter } from "next/navigation"
import SelectorPage from "@/app/selector/page"
import { api } from "@/lib/api"

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}))

jest.mock("@/lib/api", () => ({
  ...jest.requireActual("@/lib/api"),
  api: {
    comercios: {
      misComercio: jest.fn(),
    },
  },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) {
      super(message)
    }
  },
}))

describe("SelectorPage", () => {
  const mockReplace = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useRouter as jest.Mock).mockReturnValue({ replace: mockReplace, push: jest.fn() })
    Object.defineProperty(window, "localStorage", {
      value: { setItem: jest.fn(), getItem: jest.fn(), removeItem: jest.fn() },
      writable: true,
    })
  })

  it("muestra estado de carga inicial", () => {
    ;(api.comercios.misComercio as jest.Mock).mockReturnValue(new Promise(() => {}))
    render(<SelectorPage />)
    expect(screen.getByTestId("loading")).toBeInTheDocument()
  })

  it("muestra mensaje cuando el usuario no tiene comercios", async () => {
    ;(api.comercios.misComercio as jest.Mock).mockResolvedValue({ comercios: [] })
    render(<SelectorPage />)
    await waitFor(() => {
      expect(screen.getByTestId("sin-comercios")).toBeInTheDocument()
    })
  })

  it("muestra la lista cuando el usuario tiene comercios", async () => {
    ;(api.comercios.misComercio as jest.Mock).mockResolvedValue({
      comercios: [
        { id: "uuid-1", name: "Pizzería Norte", address: "Av. Corrientes 123", logo_url: null, is_active: true, role: "owner" },
        { id: "uuid-2", name: "Pizzería Sur", address: null, logo_url: null, is_active: true, role: "cashier" },
      ],
    })
    render(<SelectorPage />)
    await waitFor(() => {
      expect(screen.getByTestId("lista-comercios")).toBeInTheDocument()
      expect(screen.getByText("Pizzería Norte")).toBeInTheDocument()
      expect(screen.getByText("Pizzería Sur")).toBeInTheDocument()
    })
  })

  it("redirige al login si no está autenticado", async () => {
    const { ApiError } = jest.requireMock("@/lib/api")
    ;(api.comercios.misComercio as jest.Mock).mockRejectedValue(new ApiError(401, "No autenticado"))
    render(<SelectorPage />)
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/login")
    })
  })

  it("muestra el título de la sección", async () => {
    ;(api.comercios.misComercio as jest.Mock).mockResolvedValue({ comercios: [] })
    render(<SelectorPage />)
    await waitFor(() => {
      expect(screen.getByTestId("selector-title")).toBeInTheDocument()
    })
  })
})
