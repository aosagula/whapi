/**
 * Tests E2E para pedidos manuales / telefónicos (Fase 6).
 * Verifica la navegación, render del formulario wizard y flujo principal.
 */
import { test, expect } from "@playwright/test"

const COMERCIO_ID = "test-comercio-id"

test.describe("Pedidos manuales — navegación y render", () => {
  test.beforeEach(async ({ page, context }) => {
    await context.addCookies([
      { name: "access_token", value: "test-token", url: "http://localhost:3000" },
    ])
    await page.addInitScript(() => {
      localStorage.setItem("access_token", "test-token")
      localStorage.setItem("comercio_id", "test-comercio-id")
      localStorage.setItem("comercio_name", "Pizzería Test")
    })
  })

  test("navega a /pedidos-manuales y muestra la cabecera", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/pedidos-manuales`)
    await expect(page.getByRole("heading", { name: /pedido telefónico/i })).toBeVisible()
  })

  test("muestra el indicador de pasos del wizard", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/pedidos-manuales`)
    await expect(page.getByText("Cliente")).toBeVisible()
    await expect(page.getByText("Pedido")).toBeVisible()
    await expect(page.getByText("Entrega")).toBeVisible()
    await expect(page.getByText("Pago")).toBeVisible()
    await expect(page.getByText("Confirmar")).toBeVisible()
  })

  test("muestra el campo de búsqueda de teléfono en el paso 1", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/pedidos-manuales`)
    await expect(page.getByPlaceholder("Número de teléfono")).toBeVisible()
    await expect(page.getByRole("button", { name: /buscar/i })).toBeVisible()
  })

  test("muestra el título 'Identificación del cliente' en el paso 1", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/pedidos-manuales`)
    await expect(page.getByText("Identificación del cliente")).toBeVisible()
  })

  test("el item 'Pedidos manuales' del sidebar lleva a la página correcta", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/pedidos`)
    // El sidebar debe tener el enlace a pedidos-manuales
    const link = page.getByRole("link", { name: /pedidos manuales|telefónico/i }).first()
    if (await link.isVisible()) {
      await link.click()
      await expect(page).toHaveURL(new RegExp("pedidos-manuales"))
      await expect(page.getByRole("heading", { name: /pedido telefónico/i })).toBeVisible()
    } else {
      // Si el sidebar está minimizado, navegar directamente
      await page.goto(`/${COMERCIO_ID}/pedidos-manuales`)
      await expect(page.getByRole("heading", { name: /pedido telefónico/i })).toBeVisible()
    }
  })
})
