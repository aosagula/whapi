/**
 * Tests de la página de registro bifurcado.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { useRouter } from "next/navigation"
import RegistroPage from "@/app/(auth)/registro/page"
import { api } from "@/lib/api"

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}))

jest.mock("@/lib/api", () => ({
  ...jest.requireActual("@/lib/api"),
  api: {
    auth: {
      registro: jest.fn(),
    },
  },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) {
      super(message)
    }
  },
}))

describe("RegistroPage", () => {
  const mockPush = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useRouter as jest.Mock).mockReturnValue({ push: mockPush })
    Object.defineProperty(window, "localStorage", {
      value: { setItem: jest.fn(), getItem: jest.fn() },
      writable: true,
    })
  })

  it("renderiza la selección de tipo en el paso 1", () => {
    render(<RegistroPage />)
    expect(screen.getByTestId("tipo-dueno")).toBeInTheDocument()
    expect(screen.getByTestId("tipo-empleado")).toBeInTheDocument()
  })

  it("avanza al paso 2 al elegir tipo dueño", () => {
    render(<RegistroPage />)
    fireEvent.click(screen.getByTestId("tipo-dueno"))
    expect(screen.getByLabelText(/nombre completo/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument()
  })

  it("avanza al paso 2 al elegir tipo empleado", () => {
    render(<RegistroPage />)
    fireEvent.click(screen.getByTestId("tipo-empleado"))
    expect(screen.getByLabelText(/nombre completo/i)).toBeInTheDocument()
  })

  it("vuelve al paso 1 con el botón volver", () => {
    render(<RegistroPage />)
    fireEvent.click(screen.getByTestId("tipo-dueno"))
    fireEvent.click(screen.getByRole("button", { name: /volver/i }))
    expect(screen.getByTestId("tipo-dueno")).toBeInTheDocument()
  })

  it("registra y redirige al selector en registro exitoso", async () => {
    ;(api.auth.registro as jest.Mock).mockResolvedValue({
      id: "uuid",
      name: "Test",
      email: "test@test.com",
      phone: null,
      is_active: true,
      account_type: "owner",
      created_at: new Date().toISOString(),
      token: { access_token: "tok", token_type: "bearer" },
    })

    render(<RegistroPage />)
    fireEvent.click(screen.getByTestId("tipo-dueno"))

    fireEvent.change(screen.getByLabelText(/nombre completo/i), { target: { value: "Test User" } })
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "test@test.com" } })
    fireEvent.change(screen.getByLabelText(/contraseña/i), { target: { value: "password123" } })
    fireEvent.click(screen.getByRole("button", { name: /crear cuenta/i }))

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/selector")
    })
  })

  it("muestra error si el email ya está registrado", async () => {
    const { ApiError } = jest.requireMock("@/lib/api")
    ;(api.auth.registro as jest.Mock).mockRejectedValue(new ApiError(409, "Ya existe una cuenta"))

    render(<RegistroPage />)
    fireEvent.click(screen.getByTestId("tipo-empleado"))
    fireEvent.change(screen.getByLabelText(/nombre completo/i), { target: { value: "Test" } })
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "dup@test.com" } })
    fireEvent.change(screen.getByLabelText(/contraseña/i), { target: { value: "password123" } })
    fireEvent.click(screen.getByRole("button", { name: /crear cuenta/i }))

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/ya existe una cuenta/i)
    })
  })
})
