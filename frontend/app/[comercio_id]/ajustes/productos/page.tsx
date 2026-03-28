"use client"

/**
 * ABM de productos del catálogo.
 * Permite crear, editar y activar/desactivar productos del inventario.
 */
import { useEffect, useState, useCallback } from "react"
import { useParams } from "next/navigation"
import { Plus, Pencil, Ban, Search, X, ChevronLeft, ChevronRight, CheckCircle } from "lucide-react"
import { api, type ProductResponse, type ProductCategory, type CatalogItemData } from "@/lib/api"
import { ApiError } from "@/lib/api"

// ── Helpers ───────────────────────────────────────────────────────────────────

const CATEGORY_LABELS: Record<ProductCategory, string> = {
  pizza: "Pizza",
  empanada: "Empanada",
  drink: "Bebida",
}

const CATEGORY_OPTIONS: { value: ProductCategory | ""; label: string }[] = [
  { value: "", label: "Todas" },
  { value: "pizza", label: "Pizzas" },
  { value: "empanada", label: "Empanadas" },
  { value: "drink", label: "Bebidas" },
]

function formatPrice(n: number | null | undefined) {
  if (n == null) return "—"
  return `$${Number(n).toLocaleString("es-AR", { minimumFractionDigits: 0 })}`
}

// ── Modal de producto ─────────────────────────────────────────────────────────

interface ProductFormData {
  code: string
  short_name: string
  full_name: string
  description: string
  category: ProductCategory
  is_available: boolean
  price_large: string
  price_small: string
  price_unit: string
  price_dozen: string
}

const EMPTY_FORM: ProductFormData = {
  code: "",
  short_name: "",
  full_name: "",
  description: "",
  category: "pizza",
  is_available: true,
  price_large: "",
  price_small: "",
  price_unit: "",
  price_dozen: "",
}

interface ProductModalProps {
  comercioId: string
  editing: ProductResponse | null
  onClose: () => void
  onSaved: () => void
}

function ProductModal({ comercioId, editing, onClose, onSaved }: ProductModalProps) {
  const [form, setForm] = useState<ProductFormData>(() => {
    if (!editing) return EMPTY_FORM
    const ci = editing.catalog_item
    return {
      code: editing.code,
      short_name: editing.short_name,
      full_name: editing.full_name,
      description: editing.description ?? "",
      category: editing.category,
      is_available: editing.is_available,
      price_large: ci?.price_large != null ? String(ci.price_large) : "",
      price_small: ci?.price_small != null ? String(ci.price_small) : "",
      price_unit: ci?.price_unit != null ? String(ci.price_unit) : "",
      price_dozen: ci?.price_dozen != null ? String(ci.price_dozen) : "",
    }
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function set(field: keyof ProductFormData, value: string | boolean) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)

    try {
      let product: ProductResponse
      if (editing) {
        product = await api.productos.editar(comercioId, editing.id, {
          short_name: form.short_name,
          full_name: form.full_name,
          description: form.description || undefined,
          is_available: form.is_available,
        })
      } else {
        product = await api.productos.crear(comercioId, {
          code: form.code,
          short_name: form.short_name,
          full_name: form.full_name,
          description: form.description || undefined,
          category: form.category,
          is_available: form.is_available,
        })
      }

      // Guardar precios según categoría
      const hasPrices =
        form.price_large || form.price_small || form.price_unit || form.price_dozen
      if (hasPrices) {
        await api.productos.crearOActualizarPrecios(comercioId, {
          product_id: product.id,
          price_large: form.price_large ? Number(form.price_large) : undefined,
          price_small: form.price_small ? Number(form.price_small) : undefined,
          price_unit: form.price_unit ? Number(form.price_unit) : undefined,
          price_dozen: form.price_dozen ? Number(form.price_dozen) : undefined,
        })
      }

      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar el producto")
    } finally {
      setSaving(false)
    }
  }

  const isEditing = !!editing

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-border">
          <h2 className="font-serif text-xl text-brown">
            {isEditing ? "Editar producto" : "Nuevo producto"}
          </h2>
          <button
            onClick={onClose}
            aria-label="Cerrar"
            className="p-1.5 text-brown-muted hover:text-brown rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {/* Código — inmutable en edición */}
          <div>
            <label className="block text-sm font-medium text-brown mb-1">
              Código / ID <span className="text-red-500">*</span>
            </label>
            <input
              data-testid="input-codigo"
              value={form.code}
              onChange={(e) => set("code", e.target.value.toUpperCase())}
              disabled={isEditing}
              placeholder="PIZ-MOZ"
              required
              className={`w-full border rounded-xl px-3 py-2 text-sm text-brown focus:outline-none focus:ring-2 focus:ring-brand/30 ${
                isEditing
                  ? "bg-[#f5f0e8] text-brown-muted cursor-not-allowed border-border"
                  : "border-border bg-white"
              }`}
            />
            {isEditing && (
              <p className="text-xs text-brown-muted mt-1">El código no puede editarse una vez creado.</p>
            )}
          </div>

          {/* Categoría — inmutable en edición */}
          <div>
            <label className="block text-sm font-medium text-brown mb-1">
              Categoría <span className="text-red-500">*</span>
            </label>
            <select
              data-testid="select-categoria"
              value={form.category}
              onChange={(e) => set("category", e.target.value as ProductCategory)}
              disabled={isEditing}
              required
              className={`w-full border rounded-xl px-3 py-2 text-sm text-brown focus:outline-none focus:ring-2 focus:ring-brand/30 ${
                isEditing ? "bg-[#f5f0e8] text-brown-muted cursor-not-allowed border-border" : "border-border bg-white"
              }`}
            >
              <option value="pizza">Pizza</option>
              <option value="empanada">Empanada</option>
              <option value="drink">Bebida</option>
            </select>
          </div>

          {/* Nombre corto */}
          <div>
            <label className="block text-sm font-medium text-brown mb-1">
              Nombre corto <span className="text-red-500">*</span>
              <span className="text-brown-muted font-normal ml-1">(máx. 30 caracteres)</span>
            </label>
            <input
              data-testid="input-nombre-corto"
              value={form.short_name}
              onChange={(e) => set("short_name", e.target.value)}
              maxLength={30}
              required
              placeholder="Mozza"
              className="w-full border border-border rounded-xl px-3 py-2 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30"
            />
          </div>

          {/* Nombre completo */}
          <div>
            <label className="block text-sm font-medium text-brown mb-1">
              Nombre completo <span className="text-red-500">*</span>
            </label>
            <input
              data-testid="input-nombre-completo"
              value={form.full_name}
              onChange={(e) => set("full_name", e.target.value)}
              maxLength={150}
              required
              placeholder="Pizza Mozzarella"
              className="w-full border border-border rounded-xl px-3 py-2 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30"
            />
          </div>

          {/* Descripción */}
          <div>
            <label className="block text-sm font-medium text-brown mb-1">Descripción</label>
            <textarea
              data-testid="input-descripcion"
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
              rows={3}
              placeholder="Ingredientes o contenido..."
              className="w-full border border-border rounded-xl px-3 py-2 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30 resize-none"
            />
          </div>

          {/* Precios según categoría */}
          {form.category === "pizza" && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-brown mb-1">Precio grande</label>
                <input
                  data-testid="input-precio-grande"
                  type="number"
                  min={0}
                  step={0.01}
                  value={form.price_large}
                  onChange={(e) => set("price_large", e.target.value)}
                  placeholder="2100"
                  className="w-full border border-border rounded-xl px-3 py-2 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-brown mb-1">Precio chica</label>
                <input
                  data-testid="input-precio-chica"
                  type="number"
                  min={0}
                  step={0.01}
                  value={form.price_small}
                  onChange={(e) => set("price_small", e.target.value)}
                  placeholder="1400"
                  className="w-full border border-border rounded-xl px-3 py-2 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30"
                />
              </div>
            </div>
          )}

          {form.category === "empanada" && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-brown mb-1">Precio unitario</label>
                <input
                  data-testid="input-precio-unitario"
                  type="number"
                  min={0}
                  step={0.01}
                  value={form.price_unit}
                  onChange={(e) => set("price_unit", e.target.value)}
                  placeholder="300"
                  className="w-full border border-border rounded-xl px-3 py-2 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-brown mb-1">Precio docena</label>
                <input
                  data-testid="input-precio-docena"
                  type="number"
                  min={0}
                  step={0.01}
                  value={form.price_dozen}
                  onChange={(e) => set("price_dozen", e.target.value)}
                  placeholder="3200"
                  className="w-full border border-border rounded-xl px-3 py-2 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30"
                />
              </div>
            </div>
          )}

          {form.category === "drink" && (
            <div>
              <label className="block text-sm font-medium text-brown mb-1">Precio</label>
              <input
                data-testid="input-precio-unitario"
                type="number"
                min={0}
                step={0.01}
                value={form.price_unit}
                onChange={(e) => set("price_unit", e.target.value)}
                placeholder="400"
                className="w-full border border-border rounded-xl px-3 py-2 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30"
              />
            </div>
          )}

          {/* Disponible */}
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-brown">Disponible</label>
            <div className="flex items-center gap-4">
              {[true, false].map((v) => (
                <label key={String(v)} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="is_available"
                    value={String(v)}
                    checked={form.is_available === v}
                    onChange={() => set("is_available", v)}
                    className="accent-brand"
                  />
                  <span className="text-sm text-brown">{v ? "Sí" : "No"}</span>
                </label>
              ))}
            </div>
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-xl">{error}</p>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-sm font-medium text-brown-muted border border-border hover:bg-[#f5f0e8] transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              data-testid="btn-guardar-producto"
              disabled={saving}
              className="px-5 py-2 rounded-xl text-sm font-semibold bg-brand text-white hover:bg-brand/90 transition-colors disabled:opacity-60"
            >
              {saving ? "Guardando…" : "Guardar producto"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function ProductosPage() {
  const params = useParams()
  const comercioId = params.comercio_id as string

  const [products, setProducts] = useState<ProductResponse[]>([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState("")
  const [categoryFilter, setCategoryFilter] = useState<ProductCategory | "">("")
  const [availableFilter, setAvailableFilter] = useState<"" | "true" | "false">("")
  const [loading, setLoading] = useState(true)

  const [modalOpen, setModalOpen] = useState(false)
  const [editingProduct, setEditingProduct] = useState<ProductResponse | null>(null)

  const PAGE_SIZE = 10

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.productos.listar(comercioId, {
        search: search || undefined,
        category: categoryFilter || undefined,
        is_available: availableFilter === "" ? undefined : availableFilter === "true",
        page,
        page_size: PAGE_SIZE,
      })
      setProducts(res.items)
      setTotal(res.total)
      setTotalPages(res.total_pages)
    } catch {
      // silenciar errores de carga
    } finally {
      setLoading(false)
    }
  }, [comercioId, search, categoryFilter, availableFilter, page])

  useEffect(() => {
    load()
  }, [load])

  function openCreate() {
    setEditingProduct(null)
    setModalOpen(true)
  }

  function openEdit(p: ProductResponse) {
    setEditingProduct(p)
    setModalOpen(true)
  }

  async function handleToggleAvailable(p: ProductResponse) {
    try {
      await api.productos.editar(comercioId, p.id, { is_available: !p.is_available })
      load()
    } catch {
      // silenciar
    }
  }

  function handleSaved() {
    setModalOpen(false)
    load()
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Cabecera */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-serif text-3xl text-brown">Productos</h1>
          <p className="text-brown-muted text-sm mt-0.5">
            {total} producto{total !== 1 ? "s" : ""} en el inventario
          </p>
        </div>
        <button
          data-testid="btn-nuevo-producto"
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2 bg-brand text-white rounded-xl text-sm font-semibold hover:bg-brand/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Nuevo producto
        </button>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="flex items-center gap-2 flex-1 min-w-[200px] border border-border rounded-xl bg-white px-3 py-2 focus-within:ring-2 focus-within:ring-brand/30">
          <Search className="w-4 h-4 text-brown-muted flex-shrink-0" />
          <input
            data-testid="input-buscar"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            placeholder="Buscar por código o nombre…"
            className="flex-1 text-sm text-brown bg-transparent focus:outline-none"
          />
        </div>

        <select
          data-testid="select-filtro-categoria"
          value={categoryFilter}
          onChange={(e) => { setCategoryFilter(e.target.value as ProductCategory | ""); setPage(1) }}
          className="border border-border rounded-xl px-3 py-2 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30"
        >
          {CATEGORY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>

        <select
          data-testid="select-filtro-estado"
          value={availableFilter}
          onChange={(e) => { setAvailableFilter(e.target.value as "" | "true" | "false"); setPage(1) }}
          className="border border-border rounded-xl px-3 py-2 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30"
        >
          <option value="">Todos</option>
          <option value="true">Disponibles</option>
          <option value="false">Desactivados</option>
        </select>
      </div>

      {/* Tabla */}
      <div className="bg-white border border-border rounded-2xl overflow-hidden">
        {loading ? (
          <div className="py-16 text-center text-brown-muted text-sm">Cargando productos…</div>
        ) : products.length === 0 ? (
          <div className="py-16 text-center text-brown-muted text-sm">
            No se encontraron productos.
          </div>
        ) : (
          <table className="w-full text-sm" data-testid="tabla-productos">
            <thead>
              <tr className="border-b border-border bg-[#faf7f2]">
                <th className="text-left px-4 py-3 font-semibold text-brown-muted">Código</th>
                <th className="text-left px-4 py-3 font-semibold text-brown-muted">Nombre corto</th>
                <th className="text-left px-4 py-3 font-semibold text-brown-muted hidden md:table-cell">Nombre completo</th>
                <th className="text-left px-4 py-3 font-semibold text-brown-muted">Categoría</th>
                <th className="text-left px-4 py-3 font-semibold text-brown-muted hidden lg:table-cell">Precios</th>
                <th className="text-left px-4 py-3 font-semibold text-brown-muted">Estado</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {products.map((p, i) => (
                <tr
                  key={p.id}
                  className={`border-b border-border last:border-0 hover:bg-[#faf7f2] transition-colors ${
                    !p.is_available ? "opacity-50" : ""
                  }`}
                >
                  <td className="px-4 py-3 font-mono text-xs text-brown-muted">{p.code}</td>
                  <td className="px-4 py-3 font-medium text-brown">{p.short_name}</td>
                  <td className="px-4 py-3 text-brown hidden md:table-cell">{p.full_name}</td>
                  <td className="px-4 py-3">
                    <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-brand-pale text-brand">
                      {CATEGORY_LABELS[p.category]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-brown-muted hidden lg:table-cell">
                    {p.category === "pizza" && p.catalog_item && (
                      <span>
                        {formatPrice(p.catalog_item.price_large)} / {formatPrice(p.catalog_item.price_small)}
                      </span>
                    )}
                    {p.category === "empanada" && p.catalog_item && (
                      <span>{formatPrice(p.catalog_item.price_unit)} u.</span>
                    )}
                    {p.category === "drink" && p.catalog_item && (
                      <span>{formatPrice(p.catalog_item.price_unit)}</span>
                    )}
                    {!p.catalog_item && <span className="italic">Sin precio</span>}
                  </td>
                  <td className="px-4 py-3">
                    {p.is_available ? (
                      <span className="flex items-center gap-1 text-green-700 text-xs font-medium">
                        <CheckCircle className="w-3.5 h-3.5" /> Activo
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-red-500 text-xs font-medium">
                        <Ban className="w-3.5 h-3.5" /> Inactivo
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 justify-end">
                      <button
                        data-testid={`btn-editar-${i}`}
                        onClick={() => openEdit(p)}
                        title="Editar"
                        className="p-1.5 rounded-lg text-brown-muted hover:text-brand hover:bg-brand-pale transition-colors"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        data-testid={`btn-toggle-${i}`}
                        onClick={() => handleToggleAvailable(p)}
                        title={p.is_available ? "Desactivar" : "Activar"}
                        className={`p-1.5 rounded-lg transition-colors ${
                          p.is_available
                            ? "text-brown-muted hover:text-red-500 hover:bg-red-50"
                            : "text-brown-muted hover:text-green-600 hover:bg-green-50"
                        }`}
                      >
                        <Ban className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Paginación */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 text-sm text-brown-muted">
          <span>
            Mostrando {Math.min((page - 1) * PAGE_SIZE + 1, total)}–{Math.min(page * PAGE_SIZE, total)} de {total}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1.5 rounded-lg border border-border hover:bg-[#f5f0e8] disabled:opacity-40 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-2">Página {page} / {totalPages}</span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1.5 rounded-lg border border-border hover:bg-[#f5f0e8] disabled:opacity-40 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Modal */}
      {modalOpen && (
        <ProductModal
          comercioId={comercioId}
          editing={editingProduct}
          onClose={() => setModalOpen(false)}
          onSaved={handleSaved}
        />
      )}
    </div>
  )
}
