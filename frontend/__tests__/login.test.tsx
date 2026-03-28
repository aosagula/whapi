/**
 * Tests de la página de login.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { useRouter } from "next/navigation"
import LoginPage from "@/app/(auth)/login/page"
import { api } from "@/lib/api"

// Mock de next/navigation
jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}))

// Mock de la API
jest.mock("@/lib/api", () => ({
  ...jest.requireActual("@/lib/api"),
  api: {
    auth: {
      login: jest.fn(),
    },
  },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) {
      super(message)
    }
  },
}))

describe("LoginPage", () => {
  const mockPush = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useRouter as jest.Mock).mockReturnValue({ push: mockPush })
    // Mock de localStorage y document.cookie
    Object.defineProperty(window, "localStorage", {
      value: { setItem: jest.fn(), getItem: jest.fn(), removeItem: jest.fn() },
      writable: true,
    })
  })

  it("renderiza el formulario de login", () => {
    render(<LoginPage />)
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /ingresar/i })).toBeInTheDocument()
  })

  it("muestra enlace a registro", () => {
    render(<LoginPage />)
    expect(screen.getByRole("link", { name: /registrate/i })).toBeInTheDocument()
  })

  it("llama a la API y redirige al selector en login exitoso", async () => {
    ;(api.auth.login as jest.Mock).mockResolvedValue({
      access_token: "token123",
      token_type: "bearer",
    })

    render(<LoginPage />)
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "user@test.com" } })
    fireEvent.change(screen.getByLabelText(/contraseña/i), { target: { value: "password" } })
    fireEvent.click(screen.getByRole("button", { name: /ingresar/i }))

    await waitFor(() => {
      expect(api.auth.login).toHaveBeenCalledWith({ email: "user@test.com", password: "password" })
      expect(mockPush).toHaveBeenCalledWith("/selector")
    })
  })

  it("muestra error en credenciales incorrectas", async () => {
    const { ApiError } = jest.requireMock("@/lib/api")
    ;(api.auth.login as jest.Mock).mockRejectedValue(new ApiError(401, "Email o contraseña incorrectos"))

    render(<LoginPage />)
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "user@test.com" } })
    fireEvent.change(screen.getByLabelText(/contraseña/i), { target: { value: "mal" } })
    fireEvent.click(screen.getByRole("button", { name: /ingresar/i }))

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/email o contraseña/i)
    })
    expect(mockPush).not.toHaveBeenCalled()
  })
})
