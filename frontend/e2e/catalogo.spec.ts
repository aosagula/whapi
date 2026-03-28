/**
 * Tests E2E para catálogo: productos y combos.
 * Verifica la navegación y el render de los elementos clave.
 * Requiere que haya sesión iniciada y un comercio seleccionado.
 */
import { test, expect } from "@playwright/test"

// Helper: ir al panel con un comercio ficticio (las páginas no requieren datos reales para renderizar)
const COMERCIO_ID = "test-comercio-id"

test.describe("Productos — navegación y render", () => {
  test.beforeEach(async ({ page, context }) => {
    // El middleware verifica la cookie access_token; la seteamos antes de navegar
    await context.addCookies([
      { name: "access_token", value: "test-token", url: "http://localhost:3000" },
    ])
    await page.addInitScript(() => {
      localStorage.setItem("access_token", "test-token")
      localStorage.setItem("comercio_id", "test-comercio-id")
      localStorage.setItem("comercio_name", "Pizzería Test")
    })
  })

  test("navega a /ajustes/productos y muestra la cabecera", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/ajustes/productos`)
    await expect(page.getByRole("heading", { name: /Productos/i })).toBeVisible()
  })

  test("muestra el botón de nuevo producto", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/ajustes/productos`)
    await expect(page.getByTestId("btn-nuevo-producto")).toBeVisible()
  })

  test("abre el modal al hacer clic en nuevo producto", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/ajustes/productos`)
    await page.getByTestId("btn-nuevo-producto").click()
    await expect(page.getByTestId("input-codigo")).toBeVisible()
    await expect(page.getByTestId("btn-guardar-producto")).toBeVisible()
  })

  test("muestra los filtros de búsqueda, categoría y estado", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/ajustes/productos`)
    await expect(page.getByTestId("input-buscar")).toBeVisible()
    await expect(page.getByTestId("select-filtro-categoria")).toBeVisible()
    await expect(page.getByTestId("select-filtro-estado")).toBeVisible()
  })

  test("el modal muestra campos de precio de pizza cuando se selecciona categoría Pizza", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/ajustes/productos`)
    await page.getByTestId("btn-nuevo-producto").click()
    // Por defecto la categoría es pizza
    await expect(page.getByTestId("input-precio-grande")).toBeVisible()
    await expect(page.getByTestId("input-precio-chica")).toBeVisible()
  })

  test("el modal muestra campos de precio de empanada al cambiar categoría", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/ajustes/productos`)
    await page.getByTestId("btn-nuevo-producto").click()
    await page.getByTestId("select-categoria").selectOption("empanada")
    await expect(page.getByTestId("input-precio-unitario")).toBeVisible()
    await expect(page.getByTestId("input-precio-docena")).toBeVisible()
  })

  test("el modal se cierra al hacer clic en Cancelar", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/ajustes/productos`)
    await page.getByTestId("btn-nuevo-producto").click()
    await expect(page.getByTestId("input-codigo")).toBeVisible()
    await page.getByRole("button", { name: /Cancelar/i }).click()
    await expect(page.getByTestId("input-codigo")).not.toBeVisible()
  })
})

test.describe("Combos — navegación y render", () => {
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

  test("navega a /ajustes/combos y muestra la cabecera", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/ajustes/combos`)
    await expect(page.getByRole("heading", { name: /Combos/i })).toBeVisible()
  })

  test("muestra el botón de nuevo combo", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/ajustes/combos`)
    await expect(page.getByTestId("btn-nuevo-combo")).toBeVisible()
  })

  test("abre el modal al hacer clic en nuevo combo", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/ajustes/combos`)
    await page.getByTestId("btn-nuevo-combo").click()
    await expect(page.getByTestId("input-codigo-combo")).toBeVisible()
    await expect(page.getByTestId("btn-guardar-combo")).toBeVisible()
  })

  test("el modal de combo tiene campo de precio y productos", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/ajustes/combos`)
    await page.getByTestId("btn-nuevo-combo").click()
    await expect(page.getByTestId("input-precio-combo")).toBeVisible()
    await expect(page.getByTestId("select-agregar-producto")).toBeVisible()
  })

  test("el modal se cierra al hacer clic en Cancelar", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/ajustes/combos`)
    await page.getByTestId("btn-nuevo-combo").click()
    await expect(page.getByTestId("input-codigo-combo")).toBeVisible()
    await page.getByRole("button", { name: /Cancelar/i }).click()
    await expect(page.getByTestId("input-codigo-combo")).not.toBeVisible()
  })

  test("el filtro de búsqueda está visible", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/ajustes/combos`)
    await expect(page.getByTestId("input-buscar-combo")).toBeVisible()
    await expect(page.getByTestId("select-filtro-estado-combo")).toBeVisible()
  })
})
