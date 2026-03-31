"use client"

/**
 * Vista de atención HITL: historial de chat + pedido en curso + acciones del operador.
 */
import { useEffect, useRef, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft, Send } from "lucide-react"
import { api, ApiError, SesionDetalle } from "@/lib/api"

const ORIGIN_LABEL: Record<string, string> = {
  whatsapp: "WhatsApp",
  phone: "Telefónico",
  operator: "Operador",
}

export default function ConversacionDetallePage() {
  const params = useParams()
  const router = useRouter()
  const comercioId = params.comercio_id as string
  const sessionId = params.session_id as string

  const [sesion, setSesion] = useState<SesionDetalle | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [mensaje, setMensaje] = useState("")
  const [enviando, setEnviando] = useState(false)
  const [accion, setAccion] = useState<string | null>(null)
  const [accionError, setAccionError] = useState<string | null>(null)

  const chatRef = useRef<HTMLDivElement>(null)

  async function cargar() {
    try {
      const data = await api.conversaciones.obtener(comercioId, sessionId)
      setSesion(data)
    } catch {
      setError("No se pudo cargar la conversación.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    cargar()
  }, [comercioId, sessionId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Scroll al final del chat cuando llegan mensajes nuevos
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight
    }
  }, [sesion?.messages.length])

  async function handleAtender() {
    setAccion("atendiendo")
    setAccionError(null)
    try {
      const updated = await api.conversaciones.atender(comercioId, sessionId)
      setSesion(updated)
    } catch (err) {
      setAccionError(err instanceof ApiError ? err.message : "Error al tomar la sesión")
    } finally {
      setAccion(null)
    }
  }

  async function handleEnviarMensaje() {
    if (!mensaje.trim()) return
    setEnviando(true)
    try {
      const msg = await api.conversaciones.enviarMensaje(comercioId, sessionId, mensaje.trim())
      setSesion((s) => s ? { ...s, messages: [...s.messages, msg] } : s)
      setMensaje("")
    } catch {
      // silencioso: el mensaje no se envió
    } finally {
      setEnviando(false)
    }
  }

  async function handleDevolverAlBot() {
    setAccion("devolviendo")
    setAccionError(null)
    try {
      const updated = await api.conversaciones.devolverAlBot(comercioId, sessionId)
      setSesion(updated)
    } catch (err) {
      setAccionError(err instanceof ApiError ? err.message : "Error")
    } finally {
      setAccion(null)
    }
  }

  async function handleCerrar() {
    if (!confirm("¿Cerrar esta conversación sin pedido? El pedido en curso será descartado.")) return
    setAccion("cerrando")
    setAccionError(null)
    try {
      await api.conversaciones.cerrar(comercioId, sessionId)
      router.push(`/${comercioId}/conversaciones`)
    } catch (err) {
      setAccionError(err instanceof ApiError ? err.message : "Error")
    } finally {
      setAccion(null)
    }
  }

  if (loading) {
    return (
      <div className="py-20 flex flex-col items-center gap-3 text-brown-muted">
        <div className="w-6 h-6 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm">Cargando conversación...</span>
      </div>
    )
  }

  if (error || !sesion) {
    return (
      <div className="py-20 text-center">
        <p className="text-red-500 text-sm mb-4">{error ?? "Conversación no encontrada."}</p>
        <button onClick={() => router.push(`/${comercioId}/conversaciones`)} className="text-sm text-amber-600 hover:underline">
          Volver al listado
        </button>
      </div>
    )
  }

  const esCerrada = sesion.status === "closed" || sesion.status === "active_bot"
  const puedeEnviar = sesion.status === "assigned_human"
  const puedeAtender = sesion.status === "waiting_operator"

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Encabezado */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div className="flex items-center gap-3">
          <button
            aria-label="Volver al listado"
            onClick={() => router.push(`/${comercioId}/conversaciones`)}
            className="p-2 rounded-lg hover:bg-stone-100 transition-colors text-brown-muted"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="font-serif text-2xl text-brown">
              {sesion.customer.name ?? "Sin nombre"}
            </h1>
            <p className="text-brown-muted text-sm">{sesion.customer.phone}</p>
          </div>
        </div>
        {sesion.assigned_operator_name && (
          <span className="text-xs text-brown-muted border border-stone-200 rounded-full px-3 py-1">
            Atendido por {sesion.assigned_operator_name}
          </span>
        )}
      </div>

      {/* Layout split */}
      <div className="flex gap-4 flex-1 min-h-0">
        {/* Panel izquierdo: chat */}
        <div className="flex flex-col flex-1 min-w-0 bg-white border border-stone-200 rounded-2xl shadow-sm overflow-hidden">
          {/* Historial de mensajes */}
          <div ref={chatRef} className="flex-1 overflow-y-auto p-4 space-y-3">
            {sesion.messages.length === 0 ? (
              <p className="text-center text-brown-muted text-sm pt-8">Sin mensajes aún.</p>
            ) : (
              sesion.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.direction === "outbound" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm ${
                      msg.direction === "outbound"
                        ? "bg-amber-500 text-white rounded-br-sm"
                        : "bg-stone-100 text-brown rounded-bl-sm"
                    }`}
                  >
                    <p>{msg.content}</p>
                    <p className={`text-xs mt-1 ${msg.direction === "outbound" ? "text-amber-100" : "text-brown-muted"}`}>
                      {new Date(msg.sent_at).toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Separador "Operador conectado" */}
          {sesion.status === "assigned_human" && (
            <div className="px-4 py-2 flex items-center gap-2 border-t border-stone-100">
              <div className="flex-1 h-px bg-stone-200" />
              <span className="text-xs text-brown-muted whitespace-nowrap">— Operador conectado —</span>
              <div className="flex-1 h-px bg-stone-200" />
            </div>
          )}

          {/* Input de mensaje */}
          {puedeEnviar && (
            <div className="p-3 border-t border-stone-200 flex gap-2">
              <input
                type="text"
                value={mensaje}
                onChange={(e) => setMensaje(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleEnviarMensaje() } }}
                placeholder="Escribir mensaje..."
                disabled={enviando}
                data-testid="input-mensaje"
                className="flex-1 border border-stone-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 disabled:opacity-50"
              />
              <button
                onClick={handleEnviarMensaje}
                disabled={enviando || !mensaje.trim()}
                data-testid="btn-enviar-mensaje"
                className="p-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 disabled:opacity-50 transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Botón tomar sesión si está esperando */}
          {puedeAtender && (
            <div className="p-3 border-t border-stone-200">
              <button
                onClick={handleAtender}
                disabled={accion === "atendiendo"}
                data-testid="btn-atender"
                className="w-full py-2 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600 disabled:opacity-50 transition-colors"
              >
                {accion === "atendiendo" ? "Conectando..." : "Tomar atención"}
              </button>
            </div>
          )}

          {/* Estado cerrado/devuelto al bot */}
          {esCerrada && (
            <div className="p-3 border-t border-stone-100 text-center text-xs text-brown-muted">
              Esta sesión {sesion.status === "closed" ? "fue cerrada" : "volvió al bot"}.
            </div>
          )}
        </div>

        {/* Panel derecho: pedido + cliente + acciones */}
        <div className="w-72 shrink-0 flex flex-col gap-4 overflow-y-auto">
          {/* Pedido en curso */}
          <div className="bg-white border border-stone-200 rounded-2xl shadow-sm p-4">
            <h2 className="font-semibold text-brown text-sm uppercase tracking-wide mb-3">Pedido en curso</h2>
            {sesion.pedido_en_curso ? (
              <div>
                <div className="space-y-1.5 mb-3">
                  {sesion.pedido_en_curso.items.length === 0 ? (
                    <p className="text-brown-muted text-xs italic">Sin ítems aún</p>
                  ) : (
                    sesion.pedido_en_curso.items.map((item, i) => (
                      <div key={i} className="flex justify-between text-sm">
                        <span className="text-brown">{item.quantity}x {item.display_name ?? "Producto"}</span>
                        <span className="text-brown-muted">${(item.quantity * item.unit_price).toFixed(2)}</span>
                      </div>
                    ))
                  )}
                </div>
                <div className="border-t border-stone-100 pt-2 flex justify-between text-sm font-semibold">
                  <span className="text-brown">Subtotal</span>
                  <span className="text-brown">${sesion.pedido_en_curso.total_amount.toFixed(2)}</span>
                </div>
                <div className="mt-2 text-xs text-brown-muted space-y-0.5">
                  <p>Entrega: {sesion.pedido_en_curso.delivery_type === "delivery" ? "🚚 Delivery" : "🏪 Retiro"}</p>
                  {sesion.pedido_en_curso.delivery_address && (
                    <p>📍 {sesion.pedido_en_curso.delivery_address}</p>
                  )}
                  <p>Origen: {ORIGIN_LABEL[sesion.pedido_en_curso.status] ?? sesion.pedido_en_curso.status}</p>
                </div>
              </div>
            ) : (
              <p className="text-brown-muted text-xs italic">Sin pedido en curso.</p>
            )}
          </div>

          {/* Datos del cliente */}
          <div className="bg-white border border-stone-200 rounded-2xl shadow-sm p-4">
            <h2 className="font-semibold text-brown text-sm uppercase tracking-wide mb-3">Datos del cliente</h2>
            <div className="space-y-1.5 text-sm">
              <div className="flex justify-between">
                <span className="text-brown-muted">Nombre</span>
                <span className="text-brown">{sesion.customer.name ?? "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-brown-muted">Teléfono</span>
                <span className="text-brown">{sesion.customer.phone}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-brown-muted">Dirección</span>
                <span className="text-brown text-right max-w-[140px] truncate">{sesion.customer.address ?? "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-brown-muted">Crédito</span>
                <span className={sesion.customer.credit_balance > 0 ? "text-green-600 font-semibold" : "text-brown"}>
                  ${sesion.customer.credit_balance.toFixed(2)}
                </span>
              </div>
            </div>
          </div>

          {/* Acciones del operador */}
          {puedeEnviar && (
            <div className="bg-white border border-stone-200 rounded-2xl shadow-sm p-4 space-y-2">
              <h2 className="font-semibold text-brown text-sm uppercase tracking-wide mb-3">Acciones</h2>
              {accionError && <p className="text-red-500 text-xs">{accionError}</p>}
              <button
                onClick={handleDevolverAlBot}
                disabled={!!accion}
                data-testid="btn-devolver-al-bot"
                className="w-full py-2 border border-stone-200 rounded-lg text-sm text-brown hover:bg-stone-50 disabled:opacity-50 transition-colors"
              >
                {accion === "devolviendo" ? "Devolviendo..." : "Devolver al bot"}
              </button>
              <button
                onClick={handleCerrar}
                disabled={!!accion}
                data-testid="btn-cerrar-sin-pedido"
                className="w-full py-2 border border-red-200 rounded-lg text-sm text-red-600 hover:bg-red-50 disabled:opacity-50 transition-colors"
              >
                {accion === "cerrando" ? "Cerrando..." : "Cerrar sin pedido"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
