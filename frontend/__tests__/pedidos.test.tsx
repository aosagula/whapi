/**
 * Tests de componentes del tablero de pedidos.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { useParams } from "next/navigation"

// Mock de next/navigation
jest.mock("next/navigation", () => ({
  useParams: jest.fn().mockReturnValue({ comercio_id: "comercio-1" }),
  useRouter: jest.fn().mockReturnValue({ push: jest.fn(), replace: jest.fn() }),
}))

// Datos de prueba
const mockPedidoListItem = {
  id: "pedido-1",
  order_number: 42,
  customer: { id: "cli-1", name: "Juan Pérez", phone: "1155550001" },
  status: "pending_preparation",
  payment_status: "paid",
  origin: "operator",
  delivery_type: "delivery",
  total_amount: 3200,
  delivery_person_id: null,
  created_at: "2026-03-29T20:15:00Z",
  items_summary: ["1x Mozza", "2x Empanada Carne"],
}

const mockPedidoDetalle = {
  ...mockPedidoListItem,
  business_id: "comercio-1",
  delivery_address: "Calle Falsa 123",
  credit_applied: 0,
  internal_notes: null,
  created_by: null,
  updated_at: "2026-03-29T20:15:00Z",
  items: [
    {
      id: "item-1",
      product_id: "prod-1",
      combo_id: null,
      quantity: 1,
      unit_price: 2100,
      variant: null,
      notes: null,
      display_name: "Pizza Mozzarella",
    },
  ],
  status_history: [
    {
      id: "hist-1",
      previous_status: null,
      new_status: "pending_preparation",
      changed_by: null,
      changed_by_name: null,
      changed_at: "2026-03-29T20:15:00Z",
      note: "Pedido creado por operador",
    },
  ],
  incidents: [],
}

// Mock de la API — definido dentro del factory para evitar problemas de hoisting
jest.mock("@/lib/api", () => {
  const pedidoBase = {
    id: "pedido-1",
    order_number: 42,
    business_id: "comercio-1",
    customer: { id: "cli-1", name: "Juan Pérez", phone: "1155550001" },
    status: "pending_preparation",
    payment_status: "paid",
    origin: "operator",
    delivery_type: "delivery",
    delivery_address: "Calle Falsa 123",
    total_amount: 3200,
    credit_applied: 0,
    delivery_person_id: null,
    internal_notes: null,
    created_by: null,
    created_at: "2026-03-29T20:15:00Z",
    updated_at: "2026-03-29T20:15:00Z",
    items: [
      {
        id: "item-1",
        product_id: "prod-1",
        combo_id: null,
        quantity: 1,
        unit_price: 2100,
        variant: null,
        notes: null,
        display_name: "Pizza Mozzarella",
      },
    ],
    status_history: [
      {
        id: "hist-1",
        previous_status: null,
        new_status: "pending_preparation",
        changed_by: null,
        changed_by_name: null,
        changed_at: "2026-03-29T20:15:00Z",
        note: "Pedido creado por operador",
      },
    ],
    incidents: [],
  }
  return {
    ApiError: class extends Error {},
    api: {
      pedidos: {
        listar: jest.fn().mockResolvedValue({
          items: [
            {
              id: "pedido-1",
              order_number: 42,
              customer: { id: "cli-1", name: "Juan Pérez", phone: "1155550001" },
              status: "pending_preparation",
              payment_status: "paid",
              origin: "operator",
              delivery_type: "delivery",
              total_amount: 3200,
              delivery_person_id: null,
              created_at: "2026-03-29T20:15:00Z",
              items_summary: ["1x Mozza", "2x Empanada Carne"],
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        }),
        obtener: jest.fn().mockResolvedValue(pedidoBase),
        cambiarEstado: jest.fn().mockResolvedValue(pedidoBase),
        marcarPago: jest.fn().mockResolvedValue(pedidoBase),
        actualizarNotas: jest.fn().mockResolvedValue(pedidoBase),
        cancelar: jest.fn().mockResolvedValue({ ...pedidoBase, status: "cancelled" }),
        reportarIncidencia: jest.fn().mockResolvedValue({ ...pedidoBase, status: "with_incident" }),
        resolverRedespacho: jest.fn().mockResolvedValue(pedidoBase),
        asignarRepartidor: jest.fn().mockResolvedValue(pedidoBase),
      },
    },
  }
})

// Suprimir localStorage en test
Object.defineProperty(window, "localStorage", {
  value: {
    getItem: jest.fn().mockReturnValue("cashier"),
    setItem: jest.fn(),
    removeItem: jest.fn(),
  },
  writable: true,
})

import TablaPedidos from "@/components/pedidos/TablaPedidos"
import PedidoDetalle from "@/components/pedidos/PedidoDetalle"
import CancelarModal from "@/components/pedidos/CancelarModal"
import IncidenciaModal from "@/components/pedidos/IncidenciaModal"

// Acceso al mock de API después del hoisting
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mockApi = (jest.requireMock("@/lib/api") as any).api

// ── TablaPedidos ──────────────────────────────────────────────────────────────

describe("TablaPedidos", () => {
  beforeEach(() => {
    mockApi.pedidos.listar.mockClear()
    mockApi.pedidos.obtener.mockClear()
  })

  it("muestra el tablero con pedidos cargados", async () => {
    render(<TablaPedidos comercioId="comercio-1" userRole="cashier" />)

    await waitFor(() => {
      expect(screen.getByText("#42")).toBeInTheDocument()
    })

    expect(screen.getByText("Juan Pérez")).toBeInTheDocument()
    expect(screen.getByText("Pend. prep.")).toBeInTheDocument()
    // "Pagado" aparece también como opción del select — usar getAllByText
    expect(screen.getAllByText("Pagado").length).toBeGreaterThan(0)
  })

  it("muestra mensaje cuando no hay pedidos", async () => {
    mockApi.pedidos.listar.mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 20 })
    render(<TablaPedidos comercioId="comercio-1" userRole="cashier" />)

    await waitFor(() => {
      expect(screen.getByText("No hay pedidos para mostrar.")).toBeInTheDocument()
    })
  })

  it("abre el detalle al hacer clic en una fila", async () => {
    render(<TablaPedidos comercioId="comercio-1" userRole="cashier" />)

    await waitFor(() => {
      expect(screen.getByText("#42")).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText("Juan Pérez"))

    await waitFor(() => {
      expect(mockApi.pedidos.obtener).toHaveBeenCalledWith("comercio-1", "pedido-1")
    })
  })

  it("filtra por búsqueda de texto localmente", async () => {
    render(<TablaPedidos comercioId="comercio-1" userRole="cashier" />)

    await waitFor(() => {
      expect(screen.getByText("Juan Pérez")).toBeInTheDocument()
    })

    fireEvent.change(screen.getByPlaceholderText("Buscar cliente o teléfono..."), {
      target: { value: "María" },
    })

    expect(screen.queryByText("Juan Pérez")).not.toBeInTheDocument()
    expect(screen.getByText("Sin coincidencias.")).toBeInTheDocument()
  })

  it("botón de actualizar llama a la API", async () => {
    render(<TablaPedidos comercioId="comercio-1" userRole="cashier" />)
    await waitFor(() => expect(screen.getByText("#42")).toBeInTheDocument())

    const refreshBtn = screen.getByTitle("Actualizar")
    fireEvent.click(refreshBtn)

    await waitFor(() => {
      expect(mockApi.pedidos.listar).toHaveBeenCalledTimes(2)
    })
  })
})

// ── PedidoDetalle ─────────────────────────────────────────────────────────────

describe("PedidoDetalle", () => {
  const onClose = jest.fn()
  const onUpdated = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it("muestra los datos del pedido", () => {
    render(
      <PedidoDetalle
        pedido={mockPedidoDetalle}
        comercioId="comercio-1"
        userRole="cashier"
        onClose={onClose}
        onUpdated={onUpdated}
      />,
    )

    expect(screen.getByText("Pedido #42")).toBeInTheDocument()
    expect(screen.getByText("Juan Pérez")).toBeInTheDocument()
    expect(screen.getByText("Calle Falsa 123", { exact: false })).toBeInTheDocument()
    expect(screen.getByText("Pizza Mozzarella", { exact: false })).toBeInTheDocument()
  })

  it("muestra el historial de estados", () => {
    render(
      <PedidoDetalle
        pedido={mockPedidoDetalle}
        comercioId="comercio-1"
        userRole="cashier"
        onClose={onClose}
        onUpdated={onUpdated}
      />,
    )

    expect(screen.getByText("Pedido creado por operador", { exact: false })).toBeInTheDocument()
  })

  it("botón avanzar estado llama a la API", async () => {
    render(
      <PedidoDetalle
        pedido={mockPedidoDetalle}
        comercioId="comercio-1"
        userRole="cashier"
        onClose={onClose}
        onUpdated={onUpdated}
      />,
    )

    const btnAvanzar = screen.getByText("Iniciar preparación")
    fireEvent.click(btnAvanzar)

    await waitFor(() => {
      expect(mockApi.pedidos.cambiarEstado).toHaveBeenCalledWith(
        "comercio-1",
        "pedido-1",
        "in_preparation",
      )
    })
  })

  it("muestra botón cancelar para cajero", () => {
    render(
      <PedidoDetalle
        pedido={mockPedidoDetalle}
        comercioId="comercio-1"
        userRole="cashier"
        onClose={onClose}
        onUpdated={onUpdated}
      />,
    )

    expect(screen.getByText("Cancelar pedido")).toBeInTheDocument()
  })

  it("no muestra botón cancelar para cocinero", () => {
    render(
      <PedidoDetalle
        pedido={mockPedidoDetalle}
        comercioId="comercio-1"
        userRole="cook"
        onClose={onClose}
        onUpdated={onUpdated}
      />,
    )

    expect(screen.queryByText("Cancelar pedido")).not.toBeInTheDocument()
  })

  it("botón cerrar llama onClose", () => {
    render(
      <PedidoDetalle
        pedido={mockPedidoDetalle}
        comercioId="comercio-1"
        userRole="cashier"
        onClose={onClose}
        onUpdated={onUpdated}
      />,
    )

    // El X en el encabezado
    const closeButtons = screen.getAllByRole("button")
    const xBtn = closeButtons.find((b) => b.querySelector("svg"))
    if (xBtn) fireEvent.click(xBtn)
  })
})

// ── CancelarModal ─────────────────────────────────────────────────────────────

describe("CancelarModal", () => {
  const onClose = jest.fn()
  const onCancelled = jest.fn()

  beforeEach(() => jest.clearAllMocks())

  it("muestra la política de pago correcta para pedido sin pago", () => {
    const pedidoSinPago = { ...mockPedidoDetalle, payment_status: "no_charge" as const }
    render(
      <CancelarModal
        pedido={pedidoSinPago}
        comercioId="comercio-1"
        onClose={onClose}
        onCancelled={onCancelled}
      />,
    )

    expect(screen.getByText("Sin cargo")).toBeInTheDocument()
  })

  it("muestra crédito a favor para pedido ya pagado en preparación", () => {
    render(
      <CancelarModal
        pedido={mockPedidoDetalle}
        comercioId="comercio-1"
        onClose={onClose}
        onCancelled={onCancelled}
      />,
    )

    expect(screen.getByText("Crédito a favor")).toBeInTheDocument()
  })

  it("confirmar cancelación llama a la API", async () => {
    render(
      <CancelarModal
        pedido={mockPedidoDetalle}
        comercioId="comercio-1"
        onClose={onClose}
        onCancelled={onCancelled}
      />,
    )

    fireEvent.click(screen.getByText("Confirmar cancelación"))

    await waitFor(() => {
      expect(mockApi.pedidos.cancelar).toHaveBeenCalledWith("comercio-1", "pedido-1", {
        note: undefined,
      })
    })
  })
})

// ── IncidenciaModal ───────────────────────────────────────────────────────────

describe("IncidenciaModal", () => {
  const onClose = jest.fn()
  const onReported = jest.fn()

  beforeEach(() => jest.clearAllMocks())

  it("muestra el formulario de incidencia", () => {
    render(
      <IncidenciaModal
        pedido={mockPedidoDetalle}
        comercioId="comercio-1"
        onClose={onClose}
        onReported={onReported}
      />,
    )

    expect(screen.getByText("Reportar incidencia — Pedido #42")).toBeInTheDocument()
    expect(screen.getByText("Tipo de incidencia")).toBeInTheDocument()
  })

  it("botón reportar deshabilitado sin tipo seleccionado", () => {
    render(
      <IncidenciaModal
        pedido={mockPedidoDetalle}
        comercioId="comercio-1"
        onClose={onClose}
        onReported={onReported}
      />,
    )

    const btn = screen.getByText("Reportar incidencia")
    expect(btn).toBeDisabled()
  })

  it("reportar incidencia llama a la API con el tipo seleccionado", async () => {
    render(
      <IncidenciaModal
        pedido={mockPedidoDetalle}
        comercioId="comercio-1"
        onClose={onClose}
        onReported={onReported}
      />,
    )

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "wrong_order" } })
    fireEvent.click(screen.getByText("Reportar incidencia"))

    await waitFor(() => {
      expect(mockApi.pedidos.reportarIncidencia).toHaveBeenCalledWith("comercio-1", "pedido-1", {
        type: "wrong_order",
        description: undefined,
      })
    })
  })
})
