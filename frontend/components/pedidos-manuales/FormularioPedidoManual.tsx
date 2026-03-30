"use client"

/**
 * Formulario wizard para cargar un pedido telefónico manual.
 * Pasos: 1) identificar cliente → 2) armar pedido → 3) tipo de entrega → 4) pago → 5) confirmar
 */

import { useState, useEffect, useCallback } from "react"
import { Search, Phone, User, MapPin, ShoppingCart, Plus, Minus, Trash2, CheckCircle2, ChevronRight, Loader2 } from "lucide-react"
import { api, type ClienteResponse, type ProductResponse, type ComboResponse, type OrderResponse, ApiError } from "@/lib/api"
import { formatCurrency } from "@/components/pedidos/order-utils"

// ── Tipos internos ────────────────────────────────────────────────────────────

type PaymentMethod = "cash" | "transfer" | "mercadopago"
type DeliveryType = "delivery" | "pickup"
type ProductVariant = "large" | "small" | "unit" | "dozen"

interface CartItem {
  key: string
  type: "product" | "combo"
  id: string
  name: string
  quantity: number
  unit_price: number
  variant: ProductVariant | null
  notes: string | null
}

interface ClienteFormData {
  phone: string
  name: string
  address: string
  has_whatsapp: boolean
}

const STEPS = [
  { n: 1, label: "Cliente" },
  { n: 2, label: "Pedido" },
  { n: 3, label: "Entrega" },
  { n: 4, label: "Pago" },
  { n: 5, label: "Confirmar" },
]

const PAYMENT_OPTIONS: { value: PaymentMethod; label: string; paymentStatus: string }[] = [
  { value: "cash",        label: "Efectivo",     paymentStatus: "cash_on_delivery" },
  { value: "transfer",    label: "Transferencia", paymentStatus: "pending_payment" },
  { value: "mercadopago", label: "MercadoPago",  paymentStatus: "pending_payment" },
]

const CATEGORY_LABELS: Record<string, string> = {
  pizza:    "Pizzas",
  empanada: "Empanadas",
  drink:    "Bebidas",
}

function getVariantPrice(product: ProductResponse, variant: ProductVariant): number {
  const ci = product.catalog_item
  if (!ci) return 0
  if (variant === "large")  return ci.price_large  ?? 0
  if (variant === "small")  return ci.price_small  ?? 0
  if (variant === "unit")   return ci.price_unit   ?? 0
  if (variant === "dozen")  return ci.price_dozen  ?? 0
  return 0
}

function getDefaultVariant(product: ProductResponse): ProductVariant | null {
  const ci = product.catalog_item
  if (!ci) return null
  if (ci.price_large  != null) return "large"
  if (ci.price_unit   != null) return "unit"
  if (ci.price_small  != null) return "small"
  if (ci.price_dozen  != null) return "dozen"
  return null
}

function variantLabel(v: ProductVariant): string {
  if (v === "large")  return "Grande"
  if (v === "small")  return "Chica"
  if (v === "unit")   return "Unidad"
  if (v === "dozen")  return "Docena"
  return v
}

function cartTotal(items: CartItem[]): number {
  return items.reduce((sum, i) => sum + i.quantity * i.unit_price, 0)
}

// ── Subcomponentes ────────────────────────────────────────────────────────────

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-1 mb-6">
      {STEPS.map((s, idx) => (
        <div key={s.n} className="flex items-center gap-1">
          <div className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-semibold transition-colors ${
            s.n < current  ? "bg-green-500 text-white" :
            s.n === current ? "bg-orange-500 text-white" :
                              "bg-gray-100 text-gray-400"
          }`}>
            {s.n < current ? <CheckCircle2 size={14} /> : s.n}
          </div>
          <span className={`text-xs hidden sm:inline ${s.n === current ? "text-orange-600 font-medium" : "text-gray-400"}`}>
            {s.label}
          </span>
          {idx < STEPS.length - 1 && (
            <ChevronRight size={14} className="text-gray-300 mx-1" />
          )}
        </div>
      ))}
    </div>
  )
}

// ── Paso 1: Identificación del cliente ───────────────────────────────────────

interface Paso1Props {
  comercioId: string
  onNext: (cliente: ClienteResponse) => void
}

function Paso1Cliente({ comercioId, onNext }: Paso1Props) {
  const [phone, setPhone] = useState("")
  const [searching, setSearching] = useState(false)
  const [found, setFound] = useState<ClienteResponse | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [form, setForm] = useState<ClienteFormData>({ phone: "", name: "", address: "", has_whatsapp: true })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async () => {
    if (!phone.trim()) return
    setSearching(true)
    setFound(null)
    setNotFound(false)
    setError(null)
    try {
      const cliente = await api.clientes.buscarPorTelefono(comercioId, phone.trim())
      setFound(cliente)
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        setNotFound(true)
        setForm(f => ({ ...f, phone: phone.trim() }))
      } else {
        setError("Error al buscar el cliente")
      }
    } finally {
      setSearching(false)
    }
  }

  const handleCreate = async () => {
    if (!form.phone.trim() || !form.name.trim()) {
      setError("El nombre y el teléfono son obligatorios")
      return
    }
    setSaving(true)
    setError(null)
    try {
      const cliente = await api.clientes.crear(comercioId, {
        phone: form.phone.trim(),
        name: form.name.trim(),
        address: form.address.trim() || undefined,
        has_whatsapp: form.has_whatsapp,
      })
      onNext(cliente)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al crear el cliente")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="font-semibold text-brown text-lg">Identificación del cliente</h2>

      {/* Búsqueda por teléfono */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Phone size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="tel"
            value={phone}
            onChange={e => setPhone(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleSearch()}
            placeholder="Número de teléfono"
            className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-300"
          />
        </div>
        <button
          onClick={handleSearch}
          disabled={searching || !phone.trim()}
          className="flex items-center gap-1.5 px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600 disabled:opacity-50 transition-colors"
        >
          {searching ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
          Buscar
        </button>
      </div>

      {error && <p className="text-red-500 text-sm">{error}</p>}

      {/* Cliente encontrado */}
      {found && (
        <div className="border border-green-200 bg-green-50 rounded-lg p-4 space-y-2">
          <div className="flex items-center gap-2 text-green-700 font-medium text-sm">
            <CheckCircle2 size={16} />
            Cliente encontrado
          </div>
          <div className="text-sm space-y-1">
            <p className="font-medium text-gray-800">{found.name ?? "Sin nombre"}</p>
            <p className="text-gray-500">{found.phone}</p>
            {found.address && <p className="text-gray-500">{found.address}</p>}
            {found.credit_balance > 0 && (
              <p className="text-purple-600 font-medium">
                Crédito disponible: {formatCurrency(found.credit_balance)}
              </p>
            )}
          </div>
          <button
            onClick={() => onNext(found)}
            className="mt-2 px-4 py-1.5 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600 transition-colors"
          >
            Continuar con este cliente
          </button>
        </div>
      )}

      {/* Cliente no encontrado → formulario de alta */}
      {notFound && (
        <div className="border rounded-lg p-4 space-y-3">
          <p className="text-sm text-gray-600 font-medium">Cliente nuevo — completá los datos</p>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Teléfono</label>
              <input
                type="tel"
                value={form.phone}
                onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-300"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Nombre *</label>
              <input
                type="text"
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="Nombre del cliente"
                className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-300"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">Dirección (opcional)</label>
            <input
              type="text"
              value={form.address}
              onChange={e => setForm(f => ({ ...f, address: e.target.value }))}
              placeholder="Calle, número, piso..."
              className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-300"
            />
          </div>

          <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
            <input
              type="checkbox"
              checked={form.has_whatsapp}
              onChange={e => setForm(f => ({ ...f, has_whatsapp: e.target.checked }))}
              className="rounded"
            />
            <span>Tiene WhatsApp</span>
            {!form.has_whatsapp && (
              <span className="text-xs text-amber-600">(no recibirá notificaciones automáticas)</span>
            )}
          </label>

          <button
            onClick={handleCreate}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600 disabled:opacity-50 transition-colors"
          >
            {saving && <Loader2 size={14} className="animate-spin" />}
            Crear cliente y continuar
          </button>
        </div>
      )}
    </div>
  )
}

// ── Paso 2: Armado del pedido ─────────────────────────────────────────────────

interface Paso2Props {
  comercioId: string
  cart: CartItem[]
  onChange: (cart: CartItem[]) => void
  onNext: () => void
  onBack: () => void
}

function Paso2Pedido({ comercioId, cart, onChange, onNext, onBack }: Paso2Props) {
  const [products, setProducts] = useState<ProductResponse[]>([])
  const [combos, setCombos] = useState<ComboResponse[]>([])
  const [activeTab, setActiveTab] = useState<"pizza" | "empanada" | "drink" | "combo">("pizza")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const [prodRes, comboRes] = await Promise.all([
          api.productos.listar(comercioId, { is_available: true, page_size: 100 }),
          api.combos.listar(comercioId, { is_available: true }),
        ])
        setProducts(prodRes.items)
        setCombos(comboRes)
      } catch {
        setError("Error al cargar el catálogo")
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [comercioId])

  const addProduct = (product: ProductResponse) => {
    const variant = getDefaultVariant(product)
    const price = variant ? getVariantPrice(product, variant) : 0
    const key = `prod-${product.id}-${variant ?? "none"}`
    const existing = cart.find(i => i.key === key)
    if (existing) {
      onChange(cart.map(i => i.key === key ? { ...i, quantity: i.quantity + 1 } : i))
    } else {
      onChange([...cart, { key, type: "product", id: product.id, name: product.full_name, quantity: 1, unit_price: price, variant, notes: null }])
    }
  }

  const addCombo = (combo: ComboResponse) => {
    const key = `combo-${combo.id}`
    const existing = cart.find(i => i.key === key)
    if (existing) {
      onChange(cart.map(i => i.key === key ? { ...i, quantity: i.quantity + 1 } : i))
    } else {
      onChange([...cart, { key, type: "combo", id: combo.id, name: combo.full_name, quantity: 1, unit_price: combo.price, variant: null, notes: null }])
    }
  }

  const changeQty = (key: string, delta: number) => {
    const updated = cart.map(i => i.key === key ? { ...i, quantity: Math.max(1, i.quantity + delta) } : i)
    onChange(updated)
  }

  const removeItem = (key: string) => onChange(cart.filter(i => i.key !== key))

  const visibleProducts = products.filter(p => p.category === activeTab)

  if (loading) return <div className="flex justify-center py-8"><Loader2 className="animate-spin text-orange-500" /></div>
  if (error) return <p className="text-red-500 text-sm">{error}</p>

  return (
    <div className="space-y-4">
      <h2 className="font-semibold text-brown text-lg">Armado del pedido</h2>

      {/* Tabs de categorías */}
      <div className="flex gap-1 border-b">
        {(["pizza", "empanada", "drink", "combo"] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? "border-orange-500 text-orange-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab === "combo" ? "Combos" : CATEGORY_LABELS[tab]}
          </button>
        ))}
      </div>

      {/* Listado de productos/combos */}
      <div className="grid grid-cols-1 gap-2 max-h-56 overflow-y-auto pr-1">
        {activeTab === "combo" ? (
          combos.length === 0 ? (
            <p className="text-gray-400 text-sm py-4 text-center">Sin combos disponibles</p>
          ) : combos.map(combo => (
            <div key={combo.id} className="flex items-center justify-between border rounded-lg px-3 py-2 hover:bg-gray-50">
              <div>
                <p className="text-sm font-medium text-gray-800">{combo.full_name}</p>
                <p className="text-xs text-gray-400">{formatCurrency(combo.price)}</p>
              </div>
              <button
                onClick={() => addCombo(combo)}
                className="p-1.5 text-orange-500 hover:bg-orange-50 rounded-lg transition-colors"
              >
                <Plus size={16} />
              </button>
            </div>
          ))
        ) : (
          visibleProducts.length === 0 ? (
            <p className="text-gray-400 text-sm py-4 text-center">Sin productos disponibles</p>
          ) : visibleProducts.map(product => {
            const ci = product.catalog_item
            if (!ci) return null
            const variant = getDefaultVariant(product)
            const price = variant ? getVariantPrice(product, variant) : 0
            return (
              <div key={product.id} className="flex items-center justify-between border rounded-lg px-3 py-2 hover:bg-gray-50">
                <div>
                  <p className="text-sm font-medium text-gray-800">{product.full_name}</p>
                  <p className="text-xs text-gray-400">
                    {variant && `${variantLabel(variant)} — `}{formatCurrency(price)}
                  </p>
                </div>
                <button
                  onClick={() => addProduct(product)}
                  className="p-1.5 text-orange-500 hover:bg-orange-50 rounded-lg transition-colors"
                >
                  <Plus size={16} />
                </button>
              </div>
            )
          })
        )}
      </div>

      {/* Carrito */}
      {cart.length > 0 && (
        <div className="border rounded-lg p-3 space-y-2 bg-gray-50">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide flex items-center gap-1.5">
            <ShoppingCart size={13} /> Pedido actual
          </p>
          {cart.map(item => (
            <div key={item.key} className="flex items-center gap-2 text-sm">
              <span className="flex-1 text-gray-700">
                {item.name}
                {item.variant && <span className="text-gray-400 ml-1">({variantLabel(item.variant)})</span>}
              </span>
              <span className="text-gray-400 text-xs">{formatCurrency(item.unit_price)}</span>
              <div className="flex items-center gap-1">
                <button onClick={() => changeQty(item.key, -1)} className="p-0.5 hover:text-orange-500"><Minus size={13} /></button>
                <span className="w-5 text-center font-medium">{item.quantity}</span>
                <button onClick={() => changeQty(item.key, 1)} className="p-0.5 hover:text-orange-500"><Plus size={13} /></button>
              </div>
              <span className="font-medium text-gray-800 w-20 text-right">{formatCurrency(item.quantity * item.unit_price)}</span>
              <button onClick={() => removeItem(item.key)} className="text-red-400 hover:text-red-600"><Trash2 size={13} /></button>
            </div>
          ))}
          <div className="pt-2 border-t flex justify-between font-semibold text-sm">
            <span>Total</span>
            <span>{formatCurrency(cartTotal(cart))}</span>
          </div>
        </div>
      )}

      <div className="flex gap-2 pt-2">
        <button onClick={onBack} className="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition-colors">Atrás</button>
        <button
          onClick={onNext}
          disabled={cart.length === 0}
          className="flex-1 px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600 disabled:opacity-50 transition-colors"
        >
          Continuar
        </button>
      </div>
    </div>
  )
}

// ── Paso 3: Tipo de entrega ───────────────────────────────────────────────────

interface Paso3Props {
  deliveryType: DeliveryType
  deliveryAddress: string
  defaultAddress: string
  onChange: (type: DeliveryType, address: string) => void
  onNext: () => void
  onBack: () => void
}

function Paso3Entrega({ deliveryType, deliveryAddress, defaultAddress, onChange, onNext, onBack }: Paso3Props) {
  const addressValue = deliveryType === "delivery" ? deliveryAddress : ""
  const canContinue = deliveryType === "pickup" || deliveryAddress.trim().length > 0

  return (
    <div className="space-y-4">
      <h2 className="font-semibold text-brown text-lg">Tipo de entrega</h2>

      <div className="grid grid-cols-2 gap-3">
        {(["delivery", "pickup"] as const).map(type => (
          <button
            key={type}
            onClick={() => onChange(type, type === "delivery" ? (deliveryAddress || defaultAddress) : "")}
            className={`p-4 border-2 rounded-xl text-sm font-medium transition-colors ${
              deliveryType === type
                ? "border-orange-500 bg-orange-50 text-orange-700"
                : "border-gray-200 text-gray-600 hover:border-gray-300"
            }`}
          >
            {type === "delivery" ? "🛵 Delivery" : "🏠 Retiro en local"}
          </button>
        ))}
      </div>

      {deliveryType === "delivery" && (
        <div>
          <label className="block text-xs text-gray-500 mb-1 flex items-center gap-1">
            <MapPin size={12} /> Dirección de entrega *
          </label>
          <input
            type="text"
            value={addressValue}
            onChange={e => onChange("delivery", e.target.value)}
            placeholder="Calle, número, piso, depto..."
            className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-300"
          />
          {defaultAddress && deliveryAddress !== defaultAddress && (
            <button
              className="mt-1 text-xs text-orange-500 hover:underline"
              onClick={() => onChange("delivery", defaultAddress)}
            >
              Usar dirección guardada: {defaultAddress}
            </button>
          )}
        </div>
      )}

      <div className="flex gap-2 pt-2">
        <button onClick={onBack} className="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition-colors">Atrás</button>
        <button
          onClick={onNext}
          disabled={!canContinue}
          className="flex-1 px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600 disabled:opacity-50 transition-colors"
        >
          Continuar
        </button>
      </div>
    </div>
  )
}

// ── Paso 4: Método de pago ────────────────────────────────────────────────────

interface Paso4Props {
  method: PaymentMethod
  onChange: (m: PaymentMethod) => void
  onNext: () => void
  onBack: () => void
}

function Paso4Pago({ method, onChange, onNext, onBack }: Paso4Props) {
  return (
    <div className="space-y-4">
      <h2 className="font-semibold text-brown text-lg">Método de pago</h2>

      <div className="grid grid-cols-1 gap-3">
        {PAYMENT_OPTIONS.map(opt => (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={`p-4 border-2 rounded-xl text-sm font-medium text-left transition-colors ${
              method === opt.value
                ? "border-orange-500 bg-orange-50 text-orange-700"
                : "border-gray-200 text-gray-600 hover:border-gray-300"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="flex gap-2 pt-2">
        <button onClick={onBack} className="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition-colors">Atrás</button>
        <button
          onClick={onNext}
          className="flex-1 px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors"
        >
          Continuar
        </button>
      </div>
    </div>
  )
}

// ── Paso 5: Confirmación ──────────────────────────────────────────────────────

interface Paso5Props {
  cliente: ClienteResponse
  cart: CartItem[]
  deliveryType: DeliveryType
  deliveryAddress: string
  paymentMethod: PaymentMethod
  onConfirm: () => Promise<void>
  onBack: () => void
  submitting: boolean
  error: string | null
}

function Paso5Confirmacion({ cliente, cart, deliveryType, deliveryAddress, paymentMethod, onConfirm, onBack, submitting, error }: Paso5Props) {
  const paymentLabel = PAYMENT_OPTIONS.find(o => o.value === paymentMethod)?.label ?? paymentMethod

  return (
    <div className="space-y-4">
      <h2 className="font-semibold text-brown text-lg">Confirmar pedido</h2>

      <div className="border rounded-xl divide-y text-sm">
        {/* Cliente */}
        <div className="p-3 flex gap-2">
          <User size={15} className="text-gray-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-gray-500 text-xs">Cliente</p>
            <p className="font-medium">{cliente.name ?? "Sin nombre"} — {cliente.phone}</p>
            {!cliente.has_whatsapp && (
              <p className="text-xs text-amber-600 mt-0.5">Sin WhatsApp — sin notificaciones automáticas</p>
            )}
          </div>
        </div>

        {/* Entrega */}
        <div className="p-3 flex gap-2">
          <MapPin size={15} className="text-gray-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-gray-500 text-xs">Entrega</p>
            <p className="font-medium">{deliveryType === "delivery" ? `Delivery — ${deliveryAddress}` : "Retiro en local"}</p>
          </div>
        </div>

        {/* Pago */}
        <div className="p-3 flex gap-2">
          <ShoppingCart size={15} className="text-gray-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-gray-500 text-xs">Pago</p>
            <p className="font-medium">{paymentLabel}</p>
          </div>
        </div>

        {/* Items */}
        <div className="p-3 space-y-1">
          {cart.map(item => (
            <div key={item.key} className="flex justify-between text-gray-700">
              <span>
                {item.quantity}× {item.name}
                {item.variant && <span className="text-gray-400 ml-1">({variantLabel(item.variant)})</span>}
              </span>
              <span className="font-medium">{formatCurrency(item.quantity * item.unit_price)}</span>
            </div>
          ))}
          <div className="pt-2 border-t flex justify-between font-semibold">
            <span>Total</span>
            <span>{formatCurrency(cartTotal(cart))}</span>
          </div>
        </div>
      </div>

      {error && <p className="text-red-500 text-sm">{error}</p>}

      <div className="flex gap-2 pt-2">
        <button onClick={onBack} disabled={submitting} className="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50 transition-colors">Atrás</button>
        <button
          onClick={onConfirm}
          disabled={submitting}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
        >
          {submitting && <Loader2 size={14} className="animate-spin" />}
          Confirmar pedido
        </button>
      </div>
    </div>
  )
}

// ── Componente principal ──────────────────────────────────────────────────────

interface Props {
  comercioId: string
  onPedidoCreado?: (pedido: OrderResponse) => void
}

export default function FormularioPedidoManual({ comercioId, onPedidoCreado }: Props) {
  const [step, setStep] = useState(1)
  const [cliente, setCliente] = useState<ClienteResponse | null>(null)
  const [cart, setCart] = useState<CartItem[]>([])
  const [deliveryType, setDeliveryType] = useState<DeliveryType>("delivery")
  const [deliveryAddress, setDeliveryAddress] = useState("")
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("cash")
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [success, setSuccess] = useState<OrderResponse | null>(null)

  const handleClienteConfirmado = useCallback((c: ClienteResponse) => {
    setCliente(c)
    // Pre-cargar dirección del cliente si tiene
    if (c.address) setDeliveryAddress(c.address)
    setStep(2)
  }, [])

  const handleDeliveryChange = useCallback((type: DeliveryType, address: string) => {
    setDeliveryType(type)
    setDeliveryAddress(address)
  }, [])

  const handleConfirm = async () => {
    if (!cliente) return
    setSubmitting(true)
    setSubmitError(null)

    const paymentStatus = PAYMENT_OPTIONS.find(o => o.value === paymentMethod)?.paymentStatus ?? "pending_payment"

    try {
      const pedido = await api.pedidos.crear(comercioId, {
        customer_id: cliente.id,
        origin: "phone",
        delivery_type: deliveryType,
        delivery_address: deliveryType === "delivery" ? deliveryAddress : null,
        payment_status: paymentStatus,
        total_amount: cartTotal(cart),
        credit_applied: 0,
        items: cart.map(item => ({
          product_id: item.type === "product" ? item.id : null,
          combo_id: item.type === "combo" ? item.id : null,
          quantity: item.quantity,
          unit_price: item.unit_price,
          variant: item.variant ? { size: item.variant } : null,
          notes: item.notes,
        })),
      })
      setSuccess(pedido)
      onPedidoCreado?.(pedido)
    } catch (e) {
      setSubmitError(e instanceof ApiError ? e.message : "Error al crear el pedido")
    } finally {
      setSubmitting(false)
    }
  }

  const resetForm = () => {
    setStep(1)
    setCliente(null)
    setCart([])
    setDeliveryType("delivery")
    setDeliveryAddress("")
    setPaymentMethod("cash")
    setSuccess(null)
    setSubmitError(null)
  }

  // Pedido creado con éxito
  if (success) {
    return (
      <div className="text-center space-y-4 py-8">
        <CheckCircle2 size={48} className="text-green-500 mx-auto" />
        <div>
          <p className="font-semibold text-lg text-gray-800">¡Pedido creado!</p>
          <p className="text-gray-500 text-sm">Pedido #{success.order_number} — {success.customer.name}</p>
        </div>
        <button
          onClick={resetForm}
          className="px-6 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors"
        >
          Nuevo pedido
        </button>
      </div>
    )
  }

  return (
    <div>
      <StepIndicator current={step} />

      {step === 1 && (
        <Paso1Cliente
          comercioId={comercioId}
          onNext={handleClienteConfirmado}
        />
      )}

      {step === 2 && (
        <Paso2Pedido
          comercioId={comercioId}
          cart={cart}
          onChange={setCart}
          onNext={() => setStep(3)}
          onBack={() => setStep(1)}
        />
      )}

      {step === 3 && (
        <Paso3Entrega
          deliveryType={deliveryType}
          deliveryAddress={deliveryAddress}
          defaultAddress={cliente?.address ?? ""}
          onChange={handleDeliveryChange}
          onNext={() => setStep(4)}
          onBack={() => setStep(2)}
        />
      )}

      {step === 4 && (
        <Paso4Pago
          method={paymentMethod}
          onChange={setPaymentMethod}
          onNext={() => setStep(5)}
          onBack={() => setStep(3)}
        />
      )}

      {step === 5 && cliente && (
        <Paso5Confirmacion
          cliente={cliente}
          cart={cart}
          deliveryType={deliveryType}
          deliveryAddress={deliveryAddress}
          paymentMethod={paymentMethod}
          onConfirm={handleConfirm}
          onBack={() => setStep(4)}
          submitting={submitting}
          error={submitError}
        />
      )}
    </div>
  )
}
