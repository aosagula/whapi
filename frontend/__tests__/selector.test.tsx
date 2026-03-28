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
    auth: {
      me: jest.fn(),
    },
  },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) {
      super(message)
    }
  },
}))

const OWNER_USER = {
  id: "u1",
  name: "Carlos",
  email: "carlos@test.com",
  phone: null,
  is_active: true,
  account_type: "owner" as const,
  created_at: "2024-01-01T00:00:00Z",
}

const EMPLOYEE_USER = { ...OWNER_USER, account_type: "employee" as const }

describe("SelectorPage", () => {
  const mockReplace = jest.fn()
  const mockPush = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useRouter as jest.Mock).mockReturnValue({ replace: mockReplace, push: mockPush })
    Object.defineProperty(window, "localStorage", {
      value: { setItem: jest.fn(), getItem: jest.fn(), removeItem: jest.fn() },
      writable: true,
    })
  })

  it("muestra estado de carga inicial", () => {
    ;(api.comercios.misComercio as jest.Mock).mockReturnValue(new Promise(() => {}))
    ;(api.auth.me as jest.Mock).mockReturnValue(new Promise(() => {}))
    render(<SelectorPage />)
    expect(screen.getByTestId("loading")).toBeInTheDocument()
  })

  it("muestra mensaje cuando el usuario no tiene comercios", async () => {
    ;(api.comercios.misComercio as jest.Mock).mockResolvedValue({ comercios: [] })
    ;(api.auth.me as jest.Mock).mockResolvedValue(EMPLOYEE_USER)
    render(<SelectorPage />)
    await waitFor(() => {
      expect(screen.getByTestId("sin-comercios")).toBeInTheDocument()
    })
  })

  it("dueño sin comercios ve botón para crear comercio", async () => {
    ;(api.comercios.misComercio as jest.Mock).mockResolvedValue({ comercios: [] })
    ;(api.auth.me as jest.Mock).mockResolvedValue(OWNER_USER)
    render(<SelectorPage />)
    await waitFor(() => {
      expect(screen.getByTestId("btn-crear-comercio")).toBeInTheDocument()
    })
  })

  it("empleado sin comercios no ve botón para crear comercio", async () => {
    ;(api.comercios.misComercio as jest.Mock).mockResolvedValue({ comercios: [] })
    ;(api.auth.me as jest.Mock).mockResolvedValue(EMPLOYEE_USER)
    render(<SelectorPage />)
    await waitFor(() => {
      expect(screen.queryByTestId("btn-crear-comercio")).not.toBeInTheDocument()
    })
  })

  it("muestra la lista cuando el usuario tiene comercios", async () => {
    ;(api.comercios.misComercio as jest.Mock).mockResolvedValue({
      comercios: [
        { id: "uuid-1", name: "Pizzería Norte", address: "Av. Corrientes 123", logo_url: null, is_active: true, role: "owner", half_half_surcharge: "0" },
        { id: "uuid-2", name: "Pizzería Sur", address: null, logo_url: null, is_active: true, role: "cashier", half_half_surcharge: "0" },
      ],
    })
    ;(api.auth.me as jest.Mock).mockResolvedValue(OWNER_USER)
    render(<SelectorPage />)
    await waitFor(() => {
      expect(screen.getByTestId("lista-comercios")).toBeInTheDocument()
      expect(screen.getByText("Pizzería Norte")).toBeInTheDocument()
      expect(screen.getByText("Pizzería Sur")).toBeInTheDocument()
    })
  })

  it("dueño con comercios ve el botón de nuevo comercio", async () => {
    ;(api.comercios.misComercio as jest.Mock).mockResolvedValue({
      comercios: [
        { id: "uuid-1", name: "Pizzería Norte", address: null, logo_url: null, is_active: true, role: "owner", half_half_surcharge: "0" },
      ],
    })
    ;(api.auth.me as jest.Mock).mockResolvedValue(OWNER_USER)
    render(<SelectorPage />)
    await waitFor(() => {
      expect(screen.getByTestId("btn-nuevo-comercio")).toBeInTheDocument()
    })
  })

  it("redirige al login si no está autenticado", async () => {
    const { ApiError } = jest.requireMock("@/lib/api")
    const err = new ApiError(401, "No autenticado")
    ;(api.comercios.misComercio as jest.Mock).mockRejectedValue(err)
    ;(api.auth.me as jest.Mock).mockRejectedValue(err)
    render(<SelectorPage />)
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/login")
    })
  })

  it("muestra el título de la sección", async () => {
    ;(api.comercios.misComercio as jest.Mock).mockResolvedValue({ comercios: [] })
    ;(api.auth.me as jest.Mock).mockResolvedValue(EMPLOYEE_USER)
    render(<SelectorPage />)
    await waitFor(() => {
      expect(screen.getByTestId("selector-title")).toBeInTheDocument()
    })
  })
})
