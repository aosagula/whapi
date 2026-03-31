/**
 * Tests E2E para la sección de clientes (Fase 7).
 * Verifica navegación, render del listado y detalle, y acceso al ajuste de crédito.
 */
import { test, expect } from "@playwright/test"

const COMERCIO_ID = "test-comercio-id"

test.describe("Clientes — navegación y render", () => {
  test.beforeEach(async ({ page, context }) => {
    await context.addCookies([
      { name: "access_token", value: "test-token", url: "http://localhost:3000" },
    ])
    await page.addInitScript(() => {
      localStorage.setItem("access_token", "test-token")
      localStorage.setItem("comercio_id", "test-comercio-id")
      localStorage.setItem("comercio_name", "Pizzería Test")
      localStorage.setItem("comercio_role", "owner")
    })
  })

  test("navega a /clientes y muestra la cabecera", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/clientes`)
    await expect(page.getByRole("heading", { name: /clientes/i })).toBeVisible()
  })

  test("muestra el campo de búsqueda en el listado", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/clientes`)
    await expect(page.getByPlaceholder(/buscar por nombre o teléfono/i)).toBeVisible()
    await expect(page.getByRole("button", { name: /buscar/i })).toBeVisible()
  })

  test("muestra estado vacío cuando no hay clientes", async ({ page }) => {
    // Mock de la API: respuesta vacía
    await page.route("**/comercios/*/clientes*", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 }),
      })
    })

    await page.goto(`/${COMERCIO_ID}/clientes`)
    await expect(page.getByText(/todavía no hay clientes registrados/i)).toBeVisible()
  })

  test("muestra tabla de clientes cuando hay datos", async ({ page }) => {
    await page.route("**/comercios/*/clientes*", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [
            {
              id: "cli-001",
              business_id: COMERCIO_ID,
              phone: "1155550001",
              name: "María García",
              address: "Av. Siempreviva 742",
              has_whatsapp: true,
              credit_balance: 250,
              created_at: "2026-01-10T12:00:00Z",
            },
            {
              id: "cli-002",
              business_id: COMERCIO_ID,
              phone: "1155550002",
              name: "Juan Rodríguez",
              address: null,
              has_whatsapp: false,
              credit_balance: 0,
              created_at: "2026-02-15T10:00:00Z",
            },
          ],
          total: 2,
          page: 1,
          page_size: 20,
        }),
      })
    })

    await page.goto(`/${COMERCIO_ID}/clientes`)
    await expect(page.getByText("María García")).toBeVisible()
    await expect(page.getByText("Juan Rodríguez")).toBeVisible()
    await expect(page.getByText("1155550001")).toBeVisible()
    // Crédito positivo se muestra como badge
    await expect(page.getByText("$250.00")).toBeVisible()
  })

  test("filtra clientes al escribir y buscar", async ({ page }) => {
    let callCount = 0
    await page.route("**/comercios/*/clientes*", (route) => {
      callCount++
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 }),
      })
    })

    await page.goto(`/${COMERCIO_ID}/clientes`)
    const input = page.getByPlaceholder(/buscar por nombre o teléfono/i)
    await input.fill("María")
    await page.getByRole("button", { name: /buscar/i }).click()

    // Debe haber al menos 2 llamadas: carga inicial + búsqueda
    expect(callCount).toBeGreaterThanOrEqual(2)
  })
})

test.describe("Detalle de cliente — render con datos mockeados", () => {
  const CLIENTE_ID = "cli-001"

  test.beforeEach(async ({ page, context }) => {
    await context.addCookies([
      { name: "access_token", value: "test-token", url: "http://localhost:3000" },
    ])
    await page.addInitScript(() => {
      localStorage.setItem("access_token", "test-token")
      localStorage.setItem("comercio_id", "test-comercio-id")
      localStorage.setItem("comercio_name", "Pizzería Test")
      localStorage.setItem("comercio_role", "owner")
    })

    const API = "http://localhost:8000"
    // Solo interceptar llamadas al backend (puerto 8000), no al frontend
    await page.route(`${API}/comercios/*/clientes/cli-001/creditos`, (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "cr-001",
            customer_id: CLIENTE_ID,
            amount: 250,
            reason: "Cancelación pedido #5",
            order_id: null,
            created_at: "2026-02-01T10:00:00Z",
          },
        ]),
      })
    })
    await page.route(`${API}/comercios/*/clientes/cli-001/pedidos`, (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "ped-001",
            order_number: 5,
            status: "cancelled",
            payment_status: "credit",
            origin: "whatsapp",
            delivery_type: "delivery",
            total_amount: 250,
            created_at: "2026-01-30T20:00:00Z",
          },
        ]),
      })
    })
    await page.route(`${API}/comercios/*/clientes/cli-001`, (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: CLIENTE_ID,
          business_id: "test-comercio-id",
          phone: "1155550001",
          name: "María García",
          address: "Av. Siempreviva 742",
          has_whatsapp: true,
          credit_balance: 250,
          created_at: "2026-01-10T12:00:00Z",
        }),
      })
    })
  })

  test("muestra el nombre y teléfono del cliente", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/clientes/${CLIENTE_ID}`)
    await expect(page.getByRole("heading", { name: "María García" })).toBeVisible({ timeout: 10000 })
    await expect(page.getByText("1155550001")).toBeVisible()
  })

  test("muestra el saldo de crédito", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/clientes/${CLIENTE_ID}`)
    // El saldo aparece en el bloque de crédito como número grande
    await expect(page.getByText("$250.00").first()).toBeVisible({ timeout: 10000 })
  })

  test("muestra el historial de créditos", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/clientes/${CLIENTE_ID}`)
    await expect(page.getByText("Cancelación pedido #5")).toBeVisible({ timeout: 10000 })
  })

  test("muestra el historial de pedidos", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/clientes/${CLIENTE_ID}`)
    // El número de pedido aparece en la sección "Pedidos"
    await expect(page.locator("text=#5").first()).toBeVisible({ timeout: 10000 })
    await expect(page.getByText("Cancelado")).toBeVisible()
  })

  test("el botón Ajustar abre el modal de crédito (owner)", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/clientes/${CLIENTE_ID}`)
    await expect(page.getByRole("heading", { name: "María García" })).toBeVisible({ timeout: 10000 })
    await page.getByRole("button", { name: /ajustar/i }).click()
    await expect(page.getByText("Ajustar crédito")).toBeVisible()
    await expect(page.getByPlaceholder("0.00")).toBeVisible()
  })

  test("el botón volver navega al listado", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/clientes/${CLIENTE_ID}`)
    await expect(page.getByRole("heading", { name: "María García" })).toBeVisible({ timeout: 10000 })
    await page.getByRole("button", { name: "Volver al listado" }).click()
    await expect(page).toHaveURL(new RegExp(`${COMERCIO_ID}/clientes$`))
  })
})

test.describe("Detalle de cliente — cajero no ve botón Ajustar", () => {
  const CLIENTE_ID = "cli-001"

  test.beforeEach(async ({ page, context }) => {
    await context.addCookies([
      { name: "access_token", value: "test-token", url: "http://localhost:3000" },
    ])
    await page.addInitScript(() => {
      localStorage.setItem("access_token", "test-token")
      localStorage.setItem("comercio_id", "test-comercio-id")
      localStorage.setItem("comercio_role", "cashier")
    })

    await page.route(`**/comercios/*/clientes/${CLIENTE_ID}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: CLIENTE_ID, business_id: "test-comercio-id", phone: "1155550001",
          name: "Carlos", address: null, has_whatsapp: true,
          credit_balance: 100, created_at: "2026-01-01T00:00:00Z",
        }),
      })
    })
    await page.route(`**/comercios/*/clientes/${CLIENTE_ID}/creditos`, (route) => {
      route.fulfill({ status: 200, contentType: "application/json", body: "[]" })
    })
    await page.route(`**/comercios/*/clientes/${CLIENTE_ID}/pedidos`, (route) => {
      route.fulfill({ status: 200, contentType: "application/json", body: "[]" })
    })
  })

  test("el cajero no ve el botón Ajustar crédito", async ({ page }) => {
    await page.goto(`/test-comercio-id/clientes/${CLIENTE_ID}`)
    await expect(page.getByRole("button", { name: /ajustar/i })).not.toBeVisible()
  })
})
