/**
 * Tests de componentes del catálogo (productos y combos).
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { useParams } from "next/navigation"

// Mock de la API
jest.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) {
      super(message)
      this.name = "ApiError"
    }
  },
  api: {
    productos: {
      listar: jest.fn().mockResolvedValue({
        items: [
          {
            id: "p1",
            business_id: "b1",
            code: "PIZ-MOZ",
            short_name: "Mozza",
            full_name: "Pizza Mozzarella",
            description: "Salsa, mozzarella",
            category: "pizza",
            is_available: true,
            created_at: "2025-01-01T00:00:00Z",
            updated_at: "2025-01-01T00:00:00Z",
            catalog_item: { id: "ci1", price_large: 2100, price_small: 1400, price_unit: null, price_dozen: null, is_available: true },
          },
          {
            id: "p2",
            business_id: "b1",
            code: "EMP-CAR",
            short_name: "Carne",
            full_name: "Empanada de Carne",
            description: null,
            category: "empanada",
            is_available: false,
            created_at: "2025-01-01T00:00:00Z",
            updated_at: "2025-01-01T00:00:00Z",
            catalog_item: { id: "ci2", price_large: null, price_small: null, price_unit: 300, price_dozen: 3200, is_available: false },
          },
        ],
        total: 2,
        page: 1,
        page_size: 10,
        total_pages: 1,
      }),
      crear: jest.fn(),
      editar: jest.fn(),
      eliminar: jest.fn(),
      crearOActualizarPrecios: jest.fn().mockResolvedValue({}),
    },
    combos: {
      listar: jest.fn().mockResolvedValue([
        {
          id: "c1",
          business_id: "b1",
          code: "CMB-FAM",
          short_name: "Familiar",
          full_name: "Combo Familiar",
          description: "Pizza grande + 2 bebidas",
          price: 3500,
          is_available: true,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
          items: [{ id: "ci1", product_id: "p1", quantity: 1, product: { id: "p1", code: "PIZ-MOZ", short_name: "Mozza", full_name: "Pizza Mozzarella", description: null, category: "pizza", is_available: true, created_at: "2025-01-01T00:00:00Z", updated_at: "2025-01-01T00:00:00Z", catalog_item: null, business_id: "b1" } }],
        },
      ]),
      crear: jest.fn(),
      editar: jest.fn(),
      eliminar: jest.fn(),
    },
  },
}))

jest.mock("next/navigation", () => ({
  useParams: jest.fn(),
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
}))

const CID = "test-comercio-id"

// ── Tests de Productos ─────────────────────────────────────────────────────────

describe("ProductosPage", () => {
  beforeEach(() => {
    ;(useParams as jest.Mock).mockReturnValue({ comercio_id: CID })
  })

  it("muestra la tabla con los productos cargados", async () => {
    const { default: ProductosPage } = await import(
      "@/app/[comercio_id]/ajustes/productos/page"
    )
    render(<ProductosPage />)

    await waitFor(() => {
      expect(screen.getByTestId("tabla-productos")).toBeInTheDocument()
    })

    expect(screen.getByText("PIZ-MOZ")).toBeInTheDocument()
    expect(screen.getByText("Mozza")).toBeInTheDocument()
    expect(screen.getByText("EMP-CAR")).toBeInTheDocument()
  })

  it("muestra el botón de nuevo producto", async () => {
    const { default: ProductosPage } = await import(
      "@/app/[comercio_id]/ajustes/productos/page"
    )
    render(<ProductosPage />)
    expect(screen.getByTestId("btn-nuevo-producto")).toBeInTheDocument()
  })

  it("abre el modal al hacer clic en nuevo producto", async () => {
    const { default: ProductosPage } = await import(
      "@/app/[comercio_id]/ajustes/productos/page"
    )
    render(<ProductosPage />)

    fireEvent.click(screen.getByTestId("btn-nuevo-producto"))

    await waitFor(() => {
      expect(screen.getByTestId("input-codigo")).toBeInTheDocument()
    })
    expect(screen.getByTestId("btn-guardar-producto")).toBeInTheDocument()
  })

  it("el campo código está deshabilitado al editar", async () => {
    const { default: ProductosPage } = await import(
      "@/app/[comercio_id]/ajustes/productos/page"
    )
    render(<ProductosPage />)

    await waitFor(() => {
      expect(screen.getByTestId("tabla-productos")).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId("btn-editar-0"))

    await waitFor(() => {
      expect(screen.getByTestId("input-codigo")).toBeDisabled()
    })
  })

  it("muestra filtros de búsqueda, categoría y estado", async () => {
    const { default: ProductosPage } = await import(
      "@/app/[comercio_id]/ajustes/productos/page"
    )
    render(<ProductosPage />)

    expect(screen.getByTestId("input-buscar")).toBeInTheDocument()
    expect(screen.getByTestId("select-filtro-categoria")).toBeInTheDocument()
    expect(screen.getByTestId("select-filtro-estado")).toBeInTheDocument()
  })

  it("muestra precios de pizzas (grande / chica)", async () => {
    const { default: ProductosPage } = await import(
      "@/app/[comercio_id]/ajustes/productos/page"
    )
    render(<ProductosPage />)

    await waitFor(() => {
      // $2.100 / $1.400 deben aparecer en la columna de precios
      expect(screen.getByText(/2\.100/)).toBeInTheDocument()
    })
  })
})

// ── Tests de Combos ────────────────────────────────────────────────────────────

describe("CombosPage", () => {
  beforeEach(() => {
    ;(useParams as jest.Mock).mockReturnValue({ comercio_id: CID })
  })

  it("muestra la tabla con los combos cargados", async () => {
    const { default: CombosPage } = await import(
      "@/app/[comercio_id]/ajustes/combos/page"
    )
    render(<CombosPage />)

    await waitFor(() => {
      expect(screen.getByTestId("tabla-combos")).toBeInTheDocument()
    })

    expect(screen.getByText("CMB-FAM")).toBeInTheDocument()
    expect(screen.getByText("Familiar")).toBeInTheDocument()
  })

  it("muestra el botón de nuevo combo", async () => {
    const { default: CombosPage } = await import(
      "@/app/[comercio_id]/ajustes/combos/page"
    )
    render(<CombosPage />)
    expect(screen.getByTestId("btn-nuevo-combo")).toBeInTheDocument()
  })

  it("abre el modal al hacer clic en nuevo combo", async () => {
    const { default: CombosPage } = await import(
      "@/app/[comercio_id]/ajustes/combos/page"
    )
    render(<CombosPage />)

    fireEvent.click(screen.getByTestId("btn-nuevo-combo"))

    await waitFor(() => {
      expect(screen.getByTestId("input-codigo-combo")).toBeInTheDocument()
    })
    expect(screen.getByTestId("btn-guardar-combo")).toBeInTheDocument()
  })

  it("el código del combo está deshabilitado al editar", async () => {
    const { default: CombosPage } = await import(
      "@/app/[comercio_id]/ajustes/combos/page"
    )
    render(<CombosPage />)

    await waitFor(() => {
      expect(screen.getByTestId("tabla-combos")).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId("btn-editar-combo-0"))

    await waitFor(() => {
      expect(screen.getByTestId("input-codigo-combo")).toBeDisabled()
    })
  })

  it("muestra el precio del combo", async () => {
    const { default: CombosPage } = await import(
      "@/app/[comercio_id]/ajustes/combos/page"
    )
    render(<CombosPage />)

    await waitFor(() => {
      expect(screen.getByText(/3\.500/)).toBeInTheDocument()
    })
  })

  it("muestra los productos del combo en la tabla", async () => {
    const { default: CombosPage } = await import(
      "@/app/[comercio_id]/ajustes/combos/page"
    )
    render(<CombosPage />)

    await waitFor(() => {
      expect(screen.getByText(/1×\s*Mozza/)).toBeInTheDocument()
    })
  })
})
