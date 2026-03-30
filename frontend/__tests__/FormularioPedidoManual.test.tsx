/**
 * Tests del formulario de pedido manual (Fase 6).
 * Verifica el flujo del wizard y el manejo de estados.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import FormularioPedidoManual from "@/components/pedidos-manuales/FormularioPedidoManual"
import { api, ApiError } from "@/lib/api"

// Mock del módulo de API
jest.mock("@/lib/api", () => {
  const original = jest.requireActual("@/lib/api")
  return {
    ...original,
    api: {
      clientes: {
        buscarPorTelefono: jest.fn(),
        crear: jest.fn(),
        obtener: jest.fn(),
        actualizar: jest.fn(),
      },
      productos: {
        listar: jest.fn(),
      },
      combos: {
        listar: jest.fn(),
      },
      pedidos: {
        crear: jest.fn(),
      },
    },
  }
})

const mockProductos = {
  items: [
    {
      id: "prod-1",
      business_id: "biz-1",
      code: "MUZ",
      short_name: "Muzzarella",
      full_name: "Pizza Muzzarella",
      description: null,
      category: "pizza",
      is_available: true,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
      catalog_item: { id: "ci-1", price_large: 1500, price_small: 900, price_unit: null, price_dozen: null, is_available: true },
    },
  ],
  total: 1,
  page: 1,
  page_size: 100,
  total_pages: 1,
}

const mockCombos: never[] = []

const mockCliente = {
  id: "cust-1",
  business_id: "biz-1",
  phone: "1155550001",
  name: "Juan Test",
  address: "Corrientes 123",
  has_whatsapp: true,
  credit_balance: 0,
  created_at: "2024-01-01T00:00:00Z",
}

const mockPedido = {
  id: "order-1",
  business_id: "biz-1",
  order_number: 42,
  customer: { id: "cust-1", name: "Juan Test", phone: "1155550001" },
  status: "pending_preparation",
  payment_status: "cash_on_delivery",
  origin: "phone",
  delivery_type: "delivery",
  delivery_address: "Corrientes 123",
  total_amount: 1500,
  credit_applied: 0,
  delivery_person_id: null,
  internal_notes: null,
  created_by: null,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
  items: [],
  status_history: [],
  incidents: [],
}

describe("FormularioPedidoManual", () => {
  beforeEach(() => {
    jest.clearAllMocks()
    ;(api.productos.listar as jest.Mock).mockResolvedValue(mockProductos)
    ;(api.combos.listar as jest.Mock).mockResolvedValue(mockCombos)
  })

  it("renderiza el paso 1 (identificación del cliente) al inicio", () => {
    render(<FormularioPedidoManual comercioId="biz-1" />)
    expect(screen.getByText("Identificación del cliente")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("Número de teléfono")).toBeInTheDocument()
  })

  it("muestra el indicador de pasos", () => {
    render(<FormularioPedidoManual comercioId="biz-1" />)
    expect(screen.getByText("Cliente")).toBeInTheDocument()
    expect(screen.getByText("Pedido")).toBeInTheDocument()
    expect(screen.getByText("Confirmar")).toBeInTheDocument()
  })

  it("busca un cliente por teléfono y muestra los datos si existe", async () => {
    ;(api.clientes.buscarPorTelefono as jest.Mock).mockResolvedValue(mockCliente)

    render(<FormularioPedidoManual comercioId="biz-1" />)

    await userEvent.type(screen.getByPlaceholderText("Número de teléfono"), "1155550001")
    await userEvent.click(screen.getByRole("button", { name: /buscar/i }))

    await waitFor(() => {
      expect(screen.getByText("Cliente encontrado")).toBeInTheDocument()
      expect(screen.getByText("Juan Test")).toBeInTheDocument()
    })
  })

  it("muestra formulario de alta si el cliente no existe (404)", async () => {
    ;(api.clientes.buscarPorTelefono as jest.Mock).mockRejectedValue(
      new ApiError(404, "Cliente no encontrado")
    )

    render(<FormularioPedidoManual comercioId="biz-1" />)

    await userEvent.type(screen.getByPlaceholderText("Número de teléfono"), "9999999999")
    await userEvent.click(screen.getByRole("button", { name: /buscar/i }))

    await waitFor(() => {
      expect(screen.getByText("Cliente nuevo — completá los datos")).toBeInTheDocument()
    })
  })

  it("avanza al paso 2 cuando se confirma el cliente encontrado", async () => {
    ;(api.clientes.buscarPorTelefono as jest.Mock).mockResolvedValue(mockCliente)

    render(<FormularioPedidoManual comercioId="biz-1" />)

    await userEvent.type(screen.getByPlaceholderText("Número de teléfono"), "1155550001")
    await userEvent.click(screen.getByRole("button", { name: /buscar/i }))

    await waitFor(() => screen.getByText("Continuar con este cliente"))
    await userEvent.click(screen.getByText("Continuar con este cliente"))

    await waitFor(() => {
      expect(screen.getByText("Armado del pedido")).toBeInTheDocument()
    })
  })

  it("el botón 'Continuar' del paso 2 está deshabilitado si el carrito está vacío", async () => {
    ;(api.clientes.buscarPorTelefono as jest.Mock).mockResolvedValue(mockCliente)

    render(<FormularioPedidoManual comercioId="biz-1" />)

    await userEvent.type(screen.getByPlaceholderText("Número de teléfono"), "1155550001")
    await userEvent.click(screen.getByRole("button", { name: /buscar/i }))
    await waitFor(() => screen.getByText("Continuar con este cliente"))
    await userEvent.click(screen.getByText("Continuar con este cliente"))

    await waitFor(() => screen.getByText("Armado del pedido"))

    const continuar = screen.getByRole("button", { name: /continuar/i })
    expect(continuar).toBeDisabled()
  })

  it("crea un nuevo cliente y avanza al paso 2", async () => {
    ;(api.clientes.buscarPorTelefono as jest.Mock).mockRejectedValue(new ApiError(404, "No encontrado"))
    ;(api.clientes.crear as jest.Mock).mockResolvedValue(mockCliente)

    render(<FormularioPedidoManual comercioId="biz-1" />)

    await userEvent.type(screen.getByPlaceholderText("Número de teléfono"), "1155550001")
    await userEvent.click(screen.getByRole("button", { name: /buscar/i }))

    await waitFor(() => screen.getByText("Cliente nuevo — completá los datos"))

    // Completar el nombre (el teléfono ya está pre-cargado)
    const nombreInput = screen.getByPlaceholderText("Nombre del cliente")
    await userEvent.type(nombreInput, "Juan Test")

    await userEvent.click(screen.getByRole("button", { name: /crear cliente/i }))

    await waitFor(() => {
      expect(api.clientes.crear).toHaveBeenCalledWith("biz-1", expect.objectContaining({
        name: "Juan Test",
        phone: "1155550001",
      }))
      expect(screen.getByText("Armado del pedido")).toBeInTheDocument()
    })
  })
})
