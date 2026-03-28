"use client"

/**
 * ABM de combos del catálogo.
 * Permite crear, editar y activar/desactivar combos con sus productos.
 */
import { useEffect, useState, useCallback } from "react"
import { useParams } from "next/navigation"
import { Plus, Pencil, Ban, Search, X, CheckCircle, Trash2 } from "lucide-react"
import { api, type ComboResponse, type ProductResponse, type ProductCategory } from "@/lib/api"
import { ApiError } from "@/lib/api"

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatPrice(n: number | null | undefined) {
  if (n == null) return "—"
  return `$${Number(n).toLocaleString("es-AR", { minimumFractionDigits: 0 })}`
}

const CATEGORY_LABELS: Record<ProductCategory, string> = {
  pizza: "Pizza",
  empanada: "Empanada",
  drink: "Bebida",
}

// ── Modal de combo ────────────────────────────────────────────────────────────

interface ComboItem {
  product_id: string
  quantity: number
}

interface ComboFormData {
  code: string
  short_name: string
  full_name: string
  description: string
  price: string
  is_available: boolean
  items: ComboItem[]
}

const EMPTY_FORM: ComboFormData = {
  code: "",
  short_name: "",
  full_name: "",
  description: "",
  price: "",
  is_available: true,
  items: [],
}

interface ComboModalProps {
  comercioId: string
  editing: ComboResponse | null
  allProducts: ProductResponse[]
  onClose: () => void
  onSaved: () => void
}

function ComboModal({ comercioId, editing, allProducts, onClose, onSaved }: ComboModalProps) {
  const [form, setForm] = useState<ComboFormData>(() => {
    if (!editing) return EMPTY_FORM
    return {
      code: editing.code,
      short_name: editing.short_name,
      full_name: editing.full_name,
      description: editing.description ?? "",
      price: String(editing.price),
      is_available: editing.is_available,
      items: editing.items.map((i) => ({ product_id: i.product_id, quantity: i.quantity })),
    }
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedProductId, setSelectedProductId] = useState("")

  function setField(field: keyof ComboFormData, value: unknown) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  function addItem() {
    if (!selectedProductId) return
    const already = form.items.find((i) => i.product_id === selectedProductId)
    if (already) return
    setForm((f) => ({
      ...f,
      items: [...f.items, { product_id: selectedProductId, quantity: 1 }],
    }))
    setSelectedProductId("")
  }

  function removeItem(productId: string) {
    setForm((f) => ({ ...f, items: f.items.filter((i) => i.product_id !== productId) }))
  }

  function updateQuantity(productId: string, quantity: number) {
    setForm((f) => ({
      ...f,
      items: f.items.map((i) => (i.product_id === productId ? { ...i, quantity } : i)),
    }))
  }

  // Productos disponibles que aún no están en el combo
  const availableToAdd = allProducts.filter(
    (p) => p.is_available && !form.items.some((i) => i.product_id === p.id),
  )

  function productLabel(productId: string) {
    const p = allProducts.find((x) => x.id === productId)
    return p ? `${p.code} — ${p.short_name}` : productId
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.price || isNaN(Number(form.price))) {
      setError("El precio es requerido")
      return
    }
    setSaving(true)
    setError(null)
    try {
      const payload = {
        code: form.code,
        short_name: form.short_name,
        full_name: form.full_name,
        description: form.description || undefined,
        price: Number(form.price),
        is_available: form.is_available,
        items: form.items,
      }
      if (editing) {
        await api.combos.editar(comercioId, editing.id, payload)
      } else {
        await api.combos.crear(comercioId, payload)
      }
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar el combo")
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
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-border">
          <h2 className="font-serif text-xl text-brown">
            {isEditing ? "Editar combo" : "Nuevo combo"}
          </h2>
          <button onClick={onClose} aria-label="Cerrar" className="p-1.5 text-brown-muted hover:text-brown rounded-lg">
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
              data-testid="input-codigo-combo"
              value={form.code}
              onChange={(e) => setField("code", e.target.value.toUpperCase())}
              disabled={isEditing}
              required
              placeholder="CMB-FAM"
              className={`w-full border rounded-xl px-3 py-2 text-sm text-brown focus:outline-none focus:ring-2 focus:ring-brand/30 ${
                isEditing ? "bg-[#f5f0e8] text-brown-muted cursor-not-allowed border-border" : "border-border bg-white"
              }`}
            />
            {isEditing && (
              <p className="text-xs text-brown-muted mt-1">El código no puede editarse una vez creado.</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-brown mb-1">
                Nombre corto <span className="text-red-500">*</span>
              </label>
              <input
                data-testid="input-nombre-corto-combo"
                value={form.short_name}
                onChange={(e) => setField("short_name", e.target.value)}
                maxLength={30}
                required
                placeholder="Familiar"
                className="w-full border border-border rounded-xl px-3 py-2 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-brown mb-1">
                Precio combo <span className="text-red-500">*</span>
              </label>
              <input
                data-testid="input-precio-combo"
                type="number"
                min={0}
                step={0.01}
                value={form.price}
                onChange={(e) => setField("price", e.target.value)}
                required
                placeholder="3500"
                className="w-full border border-border rounded-xl px-3 py-2 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-brown mb-1">
              Nombre completo <span className="text-red-500">*</span>
            </label>
            <input
              data-testid="input-nombre-completo-combo"
              value={form.full_name}
              onChange={(e) => setField("full_name", e.target.value)}
              maxLength={150}
              required
              placeholder="Combo Familiar"
              className="w-full border border-border rounded-xl px-3 py-2 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-brown mb-1">Descripción</label>
            <textarea
              data-testid="input-descripcion-combo"
              value={form.description}
              onChange={(e) => setField("description", e.target.value)}
              rows={2}
              placeholder="Qué incluye el combo…"
              className="w-full border border-border rounded-xl px-3 py-2 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30 resize-none"
            />
          </div>

          {/* Productos del combo */}
          <div>
            <label className="block text-sm font-medium text-brown mb-2">Productos incluidos</label>

            {form.items.length > 0 && (
              <div className="space-y-2 mb-3">
                {form.items.map((item) => (
                  <div key={item.product_id} className="flex items-center gap-2 bg-[#faf7f2] px-3 py-2 rounded-xl">
                    <span className="flex-1 text-sm text-brown truncate">{productLabel(item.product_id)}</span>
                    <input
                      type="number"
                      min={1}
                      value={item.quantity}
                      onChange={(e) => updateQuantity(item.product_id, Number(e.target.value))}
                      className="w-14 border border-border rounded-lg px-2 py-1 text-sm text-center text-brown bg-white focus:outline-none focus:ring-1 focus:ring-brand/30"
                    />
                    <span className="text-xs text-brown-muted">un.</span>
                    <button
                      type="button"
                      onClick={() => removeItem(item.product_id)}
                      className="p-1 text-brown-muted hover:text-red-500 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-2">
              <select
                value={selectedProductId}
                onChange={(e) => setSelectedProductId(e.target.value)}
                data-testid="select-agregar-producto"
                className="flex-1 border border-border rounded-xl px-3 py-2 text-sm text-brown bg-white focus:outline-none focus:ring-2 focus:ring-brand/30"
              >
                <option value="">Seleccionar producto…</option>
                {availableToAdd.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.code} — {p.short_name} ({CATEGORY_LABELS[p.category]})
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={addItem}
                disabled={!selectedProductId}
                className="px-3 py-2 rounded-xl border border-brand text-brand text-sm font-medium hover:bg-brand-pale disabled:opacity-40 transition-colors"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Disponible */}
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-brown">Disponible</label>
            <div className="flex items-center gap-4">
              {[true, false].map((v) => (
                <label key={String(v)} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="is_available_combo"
                    value={String(v)}
                    checked={form.is_available === v}
                    onChange={() => setField("is_available", v)}
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
              data-testid="btn-guardar-combo"
              disabled={saving}
              className="px-5 py-2 rounded-xl text-sm font-semibold bg-brand text-white hover:bg-brand/90 transition-colors disabled:opacity-60"
            >
              {saving ? "Guardando…" : "Guardar combo"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function CombosPage() {
  const params = useParams()
  const comercioId = params.comercio_id as string

  const [combos, setCombos] = useState<ComboResponse[]>([])
  const [allProducts, setAllProducts] = useState<ProductResponse[]>([])
  const [search, setSearch] = useState("")
  const [availableFilter, setAvailableFilter] = useState<"" | "true" | "false">("")
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingCombo, setEditingCombo] = useState<ComboResponse | null>(null)

  const loadCombos = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.combos.listar(comercioId, {
        search: search || undefined,
        is_available: availableFilter === "" ? undefined : availableFilter === "true",
      })
      setCombos(res)
    } catch {
      // silenciar
    } finally {
      setLoading(false)
    }
  }, [comercioId, search, availableFilter])

  const loadProducts = useCallback(async () => {
    try {
      const res = await api.productos.listar(comercioId, { page_size: 100 })
      setAllProducts(res.items)
    } catch {
      // silenciar
    }
  }, [comercioId])

  useEffect(() => {
    loadCombos()
    loadProducts()
  }, [loadCombos, loadProducts])

  function openCreate() {
    setEditingCombo(null)
    setModalOpen(true)
  }

  function openEdit(c: ComboResponse) {
    setEditingCombo(c)
    setModalOpen(true)
  }

  async function handleToggleAvailable(c: ComboResponse) {
    try {
      await api.combos.editar(comercioId, c.id, { is_available: !c.is_available })
      loadCombos()
    } catch {
      // silenciar
    }
  }

  function handleSaved() {
    setModalOpen(false)
    loadCombos()
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Cabecera */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-serif text-3xl text-brown">Combos</h1>
          <p className="text-brown-muted text-sm mt-0.5">
            {combos.length} combo{combos.length !== 1 ? "s" : ""} configurado{combos.length !== 1 ? "s" : ""}
          </p>
        </div>
        <button
          data-testid="btn-nuevo-combo"
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2 bg-brand text-white rounded-xl text-sm font-semibold hover:bg-brand/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Nuevo combo
        </button>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="flex items-center gap-2 flex-1 min-w-[200px] border border-border rounded-xl bg-white px-3 py-2 focus-within:ring-2 focus-within:ring-brand/30">
          <Search className="w-4 h-4 text-brown-muted flex-shrink-0" />
          <input
            data-testid="input-buscar-combo"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por código o nombre…"
            className="flex-1 text-sm text-brown bg-transparent focus:outline-none"
          />
        </div>
        <select
          data-testid="select-filtro-estado-combo"
          value={availableFilter}
          onChange={(e) => setAvailableFilter(e.target.value as "" | "true" | "false")}
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
          <div className="py-16 text-center text-brown-muted text-sm">Cargando combos…</div>
        ) : combos.length === 0 ? (
          <div className="py-16 text-center text-brown-muted text-sm">
            No se encontraron combos.
          </div>
        ) : (
          <table className="w-full text-sm" data-testid="tabla-combos">
            <thead>
              <tr className="border-b border-border bg-[#faf7f2]">
                <th className="text-left px-4 py-3 font-semibold text-brown-muted">Código</th>
                <th className="text-left px-4 py-3 font-semibold text-brown-muted">Nombre</th>
                <th className="text-left px-4 py-3 font-semibold text-brown-muted hidden md:table-cell">Contenido</th>
                <th className="text-left px-4 py-3 font-semibold text-brown-muted">Precio</th>
                <th className="text-left px-4 py-3 font-semibold text-brown-muted">Estado</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {combos.map((c, i) => (
                <tr
                  key={c.id}
                  className={`border-b border-border last:border-0 hover:bg-[#faf7f2] transition-colors ${
                    !c.is_available ? "opacity-50" : ""
                  }`}
                >
                  <td className="px-4 py-3 font-mono text-xs text-brown-muted">{c.code}</td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-brown">{c.short_name}</div>
                    {c.description && (
                      <div className="text-xs text-brown-muted truncate max-w-xs">{c.description}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    {c.items.length === 0 ? (
                      <span className="text-brown-muted italic text-xs">Sin productos</span>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {c.items.map((item) => (
                          <span
                            key={item.id}
                            className="inline-block px-1.5 py-0.5 bg-[#f5f0e8] text-brown text-xs rounded-md"
                          >
                            {item.quantity}× {item.product?.short_name ?? item.product_id.slice(0, 6)}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 font-semibold text-brand">{formatPrice(c.price)}</td>
                  <td className="px-4 py-3">
                    {c.is_available ? (
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
                        data-testid={`btn-editar-combo-${i}`}
                        onClick={() => openEdit(c)}
                        title="Editar"
                        className="p-1.5 rounded-lg text-brown-muted hover:text-brand hover:bg-brand-pale transition-colors"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        data-testid={`btn-toggle-combo-${i}`}
                        onClick={() => handleToggleAvailable(c)}
                        title={c.is_available ? "Desactivar" : "Activar"}
                        className={`p-1.5 rounded-lg transition-colors ${
                          c.is_available
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

      {/* Modal */}
      {modalOpen && (
        <ComboModal
          comercioId={comercioId}
          editing={editingCombo}
          allProducts={allProducts}
          onClose={() => setModalOpen(false)}
          onSaved={handleSaved}
        />
      )}
    </div>
  )
}
