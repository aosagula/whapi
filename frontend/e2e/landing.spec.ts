import { test, expect } from "@playwright/test"

/**
 * Tests E2E de la landing page usando Playwright MCP.
 * Valida navegación y presencia de elementos clave en el browser real.
 */
test.describe("Landing page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/")
  })

  test("carga correctamente y muestra el nombre Whapi", async ({ page }) => {
    await expect(page).toHaveTitle(/Whapi/)
    await expect(page.getByText("Whapi").first()).toBeVisible()
  })

  test("el navbar muestra los botones de acceso", async ({ page }) => {
    await expect(page.getByRole("button", { name: /iniciar sesión/i })).toBeVisible()
    await expect(page.getByRole("button", { name: /registrarse/i }).first()).toBeVisible()
  })

  test("el botón 'Iniciar sesión' navega a /login", async ({ page }) => {
    await page.getByRole("button", { name: /iniciar sesión/i }).click()
    await expect(page).toHaveURL(/\/login/)
  })

  test("el botón 'Registrarse' navega a /register", async ({ page }) => {
    await page.getByRole("button", { name: /registrarse/i }).first().click()
    await expect(page).toHaveURL(/\/register/)
  })

  test("muestra la sección hero con el headline principal", async ({ page }) => {
    const hero = page.getByTestId("hero")
    await expect(hero).toBeVisible()
    await expect(hero.getByText(/sin complicaciones/i)).toBeVisible()
  })

  test("muestra las 6 características", async ({ page }) => {
    await expect(page.getByText("Chatbot con IA")).toBeVisible()
    await expect(page.getByText("Panel en tiempo real")).toBeVisible()
    await expect(page.getByText("Pagos automáticos")).toBeVisible()
    await expect(page.getByText("Multi-sucursal")).toBeVisible()
    await expect(page.getByText("Reportes y métricas")).toBeVisible()
    await expect(page.getByText(/Operador humano/i)).toBeVisible()
  })

  test("muestra los 4 pasos de onboarding", async ({ page }) => {
    await expect(page.getByText("Registrá tu cuenta")).toBeVisible()
    await expect(page.getByText("Conectá WhatsApp")).toBeVisible()
    await expect(page.getByText("Cargá tu menú")).toBeVisible()
    await expect(page.getByText("Empezá a recibir pedidos")).toBeVisible()
  })
})
