/**
 * Tests de la página de gestión de empleados.
 */
import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import { useParams } from "next/navigation"
import EmpleadosPage from "@/app/[comercio_id]/ajustes/empleados/page"
import { api } from "@/lib/api"

jest.mock("next/navigation", () => ({
  useParams: jest.fn(),
}))

jest.mock("@/lib/api", () => ({
  ...jest.requireActual("@/lib/api"),
  api: {
    empleados: {
      listar: jest.fn(),
      asociar: jest.fn(),
      cambiarRol: jest.fn(),
      darDeBaja: jest.fn(),
    },
  },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) {
      super(message)
    }
  },
}))

const EMPLEADOS_FIXTURE = [
  {
    user_id: "uid-1",
    name: "Carlos Dueño",
    email: "carlos@test.com",
    phone: null,
    role: "owner" as const,
    is_active: true,
    joined_at: "2024-01-01T00:00:00Z",
  },
  {
    user_id: "uid-2",
    name: "Ana Cajero",
    email: "ana@test.com",
    phone: null,
    role: "cashier" as const,
    is_active: true,
    joined_at: "2024-01-02T00:00:00Z",
  },
]

describe("EmpleadosPage", () => {
  beforeEach(() => {
    jest.clearAllMocks()
    ;(useParams as jest.Mock).mockReturnValue({ comercio_id: "cid-1" })
  })

  it("muestra estado de carga inicial", () => {
    ;(api.empleados.listar as jest.Mock).mockReturnValue(new Promise(() => {}))
    render(<EmpleadosPage />)
    expect(screen.getByTestId("loading")).toBeInTheDocument()
  })

  it("muestra la lista de empleados al cargar", async () => {
    ;(api.empleados.listar as jest.Mock).mockResolvedValue(EMPLEADOS_FIXTURE)
    render(<EmpleadosPage />)
    await waitFor(() => {
      expect(screen.getByTestId("lista-empleados")).toBeInTheDocument()
      expect(screen.getByText("Carlos Dueño")).toBeInTheDocument()
      expect(screen.getByText("Ana Cajero")).toBeInTheDocument()
    })
  })

  it("el owner no tiene botón de baja", async () => {
    ;(api.empleados.listar as jest.Mock).mockResolvedValue(EMPLEADOS_FIXTURE)
    render(<EmpleadosPage />)
    await waitFor(() => {
      expect(screen.queryByLabelText("Dar de baja a Carlos Dueño")).not.toBeInTheDocument()
    })
  })

  it("el empleado no-owner tiene botón de baja", async () => {
    ;(api.empleados.listar as jest.Mock).mockResolvedValue(EMPLEADOS_FIXTURE)
    render(<EmpleadosPage />)
    await waitFor(() => {
      expect(screen.getByLabelText("Dar de baja a Ana Cajero")).toBeInTheDocument()
    })
  })

  it("muestra mensaje de éxito al asociar empleado", async () => {
    ;(api.empleados.listar as jest.Mock).mockResolvedValue([])
    ;(api.empleados.asociar as jest.Mock).mockResolvedValue({
      user_id: "uid-3",
      name: "Nuevo Empleado",
      email: "nuevo@test.com",
      phone: null,
      role: "cashier",
      is_active: true,
      joined_at: "2024-01-03T00:00:00Z",
    })
    render(<EmpleadosPage />)
    await waitFor(() => expect(screen.getByTestId("btn-asociar")).toBeInTheDocument())

    fireEvent.change(screen.getByTestId("input-email"), { target: { value: "nuevo@test.com" } })
    fireEvent.click(screen.getByTestId("btn-asociar"))

    await waitFor(() => {
      expect(screen.getByText(/Nuevo Empleado fue asociado/)).toBeInTheDocument()
    })
  })

  it("muestra error cuando falla la asociación", async () => {
    const { ApiError } = jest.requireMock("@/lib/api")
    ;(api.empleados.listar as jest.Mock).mockResolvedValue([])
    ;(api.empleados.asociar as jest.Mock).mockRejectedValue(new ApiError(404, "Usuario no encontrado"))
    render(<EmpleadosPage />)
    await waitFor(() => expect(screen.getByTestId("btn-asociar")).toBeInTheDocument())

    fireEvent.change(screen.getByTestId("input-email"), { target: { value: "noexiste@test.com" } })
    fireEvent.click(screen.getByTestId("btn-asociar"))

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Usuario no encontrado")
    })
  })

  it("muestra el formulario de asociar con selector de rol", async () => {
    ;(api.empleados.listar as jest.Mock).mockResolvedValue([])
    render(<EmpleadosPage />)
    await waitFor(() => {
      expect(screen.getByTestId("input-email")).toBeInTheDocument()
      expect(screen.getByTestId("select-rol")).toBeInTheDocument()
    })
  })
})
