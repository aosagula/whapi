/**
 * Tests E2E para conversaciones activas HITL (Fase 8).
 */
import { test, expect } from "@playwright/test"

const COMERCIO_ID = "test-comercio-id"
const SESSION_ID = "sess-001"
const API = "http://localhost:8000"

const mockSesionWaiting = {
  id: SESSION_ID,
  status: "waiting_operator",
  customer: { id: "cli-001", name: "Juan Pérez", phone: "1155551234", address: "Av. Test 123", credit_balance: 0 },
  assigned_operator_id: null,
  assigned_operator_name: null,
  pedido_en_curso: {
    id: "ped-001",
    order_number: 7,
    status: "in_progress",
    delivery_type: "delivery",
    delivery_address: "Av. Test 123",
    total_amount: 3900,
    items: [
      { display_name: "Pizza Mozzarella Grande", quantity: 1, unit_price: 2100 },
      { display_name: "Empanada Carne", quantity: 6, unit_price: 300 },
    ],
  },
  messages: [
    { id: "msg-001", direction: "inbound", content: "quiero una mozza grande y 6 empanadas", sent_at: "2026-03-30T20:00:00Z" },
    { id: "msg-002", direction: "outbound", content: "Anotado! ¿Algo más?", sent_at: "2026-03-30T20:00:05Z" },
    { id: "msg-003", direction: "inbound", content: "no, hablame con una persona", sent_at: "2026-03-30T20:00:10Z" },
  ],
  created_at: "2026-03-30T19:59:00Z",
  last_message_at: "2026-03-30T20:00:10Z",
  wait_seconds: 180,
}

const mockSesionAsignada = {
  ...mockSesionWaiting,
  status: "assigned_human",
  assigned_operator_id: "usr-001",
  assigned_operator_name: "Cajero Test",
}

test.describe("Conversaciones — listado", () => {
  test.beforeEach(async ({ page, context }) => {
    await context.addCookies([{ name: "access_token", value: "test-token", url: "http://localhost:3000" }])
    await page.addInitScript(() => {
      localStorage.setItem("access_token", "test-token")
      localStorage.setItem("comercio_id", "test-comercio-id")
      localStorage.setItem("comercio_role", "cashier")
    })
  })

  test("navega a /conversaciones y muestra la cabecera", async ({ page }) => {
    await page.route(`${API}/comercios/*/conversaciones`, (route) => {
      route.fulfill({ status: 200, contentType: "application/json", body: "[]" })
    })
    await page.goto(`/${COMERCIO_ID}/conversaciones`)
    await expect(page.getByRole("heading", { name: /conversaciones/i })).toBeVisible()
  })

  test("muestra estado vacío cuando no hay sesiones activas", async ({ page }) => {
    await page.route(`${API}/comercios/*/conversaciones`, (route) => {
      route.fulfill({ status: 200, contentType: "application/json", body: "[]" })
    })
    await page.goto(`/${COMERCIO_ID}/conversaciones`)
    await expect(page.getByText(/no hay conversaciones activas/i)).toBeVisible({ timeout: 8000 })
  })

  test("muestra sesión en waiting_operator con botón Atender", async ({ page }) => {
    await page.route(`${API}/comercios/*/conversaciones`, (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([{ ...mockSesionWaiting, messages: [] }]),
      })
    })
    await page.goto(`/${COMERCIO_ID}/conversaciones`)
    await expect(page.getByText("Juan Pérez")).toBeVisible({ timeout: 8000 })
    await expect(page.getByText("Esperando operador")).toBeVisible()
    await expect(page.getByRole("button", { name: /atender/i })).toBeVisible()
  })

  test("muestra sesión en assigned_human con botón Ver", async ({ page }) => {
    await page.route(`${API}/comercios/*/conversaciones`, (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([{ ...mockSesionAsignada, messages: [] }]),
      })
    })
    await page.goto(`/${COMERCIO_ID}/conversaciones`)
    await expect(page.getByText("En atención")).toBeVisible({ timeout: 8000 })
    await expect(page.getByRole("button", { name: /ver/i })).toBeVisible()
  })

  test("el sidebar tiene el ítem Conversaciones", async ({ page }) => {
    await page.route(`${API}/comercios/*/conversaciones`, (route) => {
      route.fulfill({ status: 200, contentType: "application/json", body: "[]" })
    })
    await page.goto(`/${COMERCIO_ID}/conversaciones`)
    await expect(page.getByTestId("nav-conversaciones")).toBeVisible()
  })
})

test.describe("Conversaciones — detalle/chat", () => {
  test.beforeEach(async ({ page, context }) => {
    await context.addCookies([{ name: "access_token", value: "test-token", url: "http://localhost:3000" }])
    await page.addInitScript(() => {
      localStorage.setItem("access_token", "test-token")
      localStorage.setItem("comercio_id", "test-comercio-id")
      localStorage.setItem("comercio_role", "cashier")
    })

    await page.route(`${API}/comercios/*/conversaciones/${SESSION_ID}`, (route) => {
      const url = route.request().url()
      if (url.endsWith(`/${SESSION_ID}`)) {
        route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mockSesionWaiting) })
      } else {
        route.continue()
      }
    })
  })

  test("navega al detalle y muestra el nombre del cliente", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/conversaciones/${SESSION_ID}`)
    await expect(page.getByRole("heading", { name: "Juan Pérez" })).toBeVisible({ timeout: 10000 })
    await expect(page.getByText("1155551234").first()).toBeVisible()
  })

  test("muestra el historial de mensajes", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/conversaciones/${SESSION_ID}`)
    await expect(page.getByText("quiero una mozza grande y 6 empanadas")).toBeVisible({ timeout: 10000 })
    await expect(page.getByText("no, hablame con una persona")).toBeVisible()
  })

  test("muestra el pedido en curso en el panel derecho", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/conversaciones/${SESSION_ID}`)
    await expect(page.getByText("Pizza Mozzarella Grande")).toBeVisible({ timeout: 10000 })
    await expect(page.getByText("$3900.00")).toBeVisible()
  })

  test("muestra los datos del cliente en el panel derecho", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/conversaciones/${SESSION_ID}`)
    // La dirección aparece en el panel de datos del cliente
    await expect(page.getByText("Av. Test 123", { exact: true })).toBeVisible({ timeout: 10000 })
  })

  test("muestra botón Tomar atención cuando la sesión está en waiting_operator", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/conversaciones/${SESSION_ID}`)
    await expect(page.getByTestId("btn-atender")).toBeVisible({ timeout: 10000 })
  })
})

test.describe("Conversaciones — detalle asignada", () => {
  test.beforeEach(async ({ page, context }) => {
    await context.addCookies([{ name: "access_token", value: "test-token", url: "http://localhost:3000" }])
    await page.addInitScript(() => {
      localStorage.setItem("access_token", "test-token")
      localStorage.setItem("comercio_id", "test-comercio-id")
      localStorage.setItem("comercio_role", "cashier")
    })

    await page.route(`${API}/comercios/*/conversaciones/${SESSION_ID}`, (route) => {
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mockSesionAsignada) })
    })
  })

  test("muestra campo de texto y botón Enviar cuando está asignada", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/conversaciones/${SESSION_ID}`)
    await expect(page.getByTestId("input-mensaje")).toBeVisible({ timeout: 10000 })
    await expect(page.getByTestId("btn-enviar-mensaje")).toBeVisible()
  })

  test("muestra botones Devolver al bot y Cerrar sin pedido", async ({ page }) => {
    await page.goto(`/${COMERCIO_ID}/conversaciones/${SESSION_ID}`)
    await expect(page.getByTestId("btn-devolver-al-bot")).toBeVisible({ timeout: 10000 })
    await expect(page.getByTestId("btn-cerrar-sin-pedido")).toBeVisible()
  })

  test("el botón volver navega al listado", async ({ page }) => {
    await page.route(`${API}/comercios/*/conversaciones`, (route) => {
      route.fulfill({ status: 200, contentType: "application/json", body: "[]" })
    })
    await page.goto(`/${COMERCIO_ID}/conversaciones/${SESSION_ID}`)
    await expect(page.getByRole("heading", { name: "Juan Pérez" })).toBeVisible({ timeout: 10000 })
    await page.getByRole("button", { name: "Volver al listado" }).click()
    await expect(page).toHaveURL(new RegExp(`${COMERCIO_ID}/conversaciones$`))
  })
})
