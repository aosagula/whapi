/**
 * Tests de la landing page (/)
 * Verifica que renderiza correctamente y muestra los elementos clave.
 */
import { render, screen } from "@testing-library/react"
import LandingPage from "@/app/page"

describe("Landing page", () => {
  it("renderiza sin errores", () => {
    render(<LandingPage />)
  })

  it("muestra el nombre del producto en el navbar", () => {
    render(<LandingPage />)
    // El nombre Whapi aparece al menos en el navbar
    const brandElements = screen.getAllByText("Whapi")
    expect(brandElements.length).toBeGreaterThanOrEqual(1)
  })

  it("muestra el botón de iniciar sesión", () => {
    render(<LandingPage />)
    expect(screen.getByRole("button", { name: /iniciar sesión/i })).toBeInTheDocument()
  })

  it("muestra el botón de registrarse", () => {
    render(<LandingPage />)
    // Hay múltiples botones de registro; con getAllByRole verificamos que existe al menos uno
    const registerButtons = screen.getAllByRole("button", { name: /registrarse|crear cuenta/i })
    expect(registerButtons.length).toBeGreaterThanOrEqual(1)
  })

  it("muestra la sección hero", () => {
    render(<LandingPage />)
    expect(screen.getByTestId("hero")).toBeInTheDocument()
  })

  it("muestra las características principales", () => {
    render(<LandingPage />)
    expect(screen.getByText("Chatbot con IA")).toBeInTheDocument()
    expect(screen.getByText("Panel en tiempo real")).toBeInTheDocument()
    expect(screen.getByText("Pagos automáticos")).toBeInTheDocument()
  })
})
