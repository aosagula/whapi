# Flujos n8n — Pizzería Chatbot

Importá cada archivo JSON desde **n8n → Workflows → Import from file**.

## Variables de entorno requeridas en n8n

Configurá en **Settings → Variables**:

| Variable | Ejemplo |
|---|---|
| `API_BASE_URL` | `http://backend:8000` |
| `WPPCONNECT_BASE_URL` | `http://wppconnect:21465` |
| `WPPCONNECT_SECRET_KEY` | (secret key de WPPConnect) |
| `OPENAI_API_KEY` | (API key de OpenAI) |

Para el nodo de credencial Bearer (API interna), configurá en n8n una credencial **HTTP Bearer Auth** con el JWT de un usuario con rol `admin` o `cajero`.

---

## chatbot-principal.json

Procesa mensajes entrantes, construye contexto completo para el LLM y enruta acciones.

**Trigger:** `POST /webhook/chatbot-mensaje`

**Payload esperado:**
```json
{
  "pizzeria_id": 1,
  "session_id": 42,
  "status": "active",
  "message": "Quiero pedir una pizza",
  "customer_phone": "5491112345678"
}
```

**Flujo:**
1. Si la sesión está en `transferred_human` o `waiting_human` → ignora (HITL activo)
2. Obtiene contexto de sesión (historial + datos del cliente + crédito)
3. Obtiene catálogo de productos y combos disponibles
4. Obtiene pedido activo (`in_progress`) del cliente
5. Construye prompt de sistema con todo el contexto (Code node)
6. Llama a OpenAI GPT-4o-mini con salida JSON estructurada
7. Enruta por acción detectada:
   - `reply` → guarda el mensaje y lo envía por WPPConnect
   - `confirm_order` → crea el pedido vía API → guarda y envía mensaje
   - `request_human` → cambia estado de sesión a `waiting_human` → guarda y envía mensaje
   - `cancel_order` → cancela pedido activo → guarda y envía mensaje
   - `update_client` → actualiza nombre/dirección del cliente → guarda y envía mensaje

**Formato de respuesta del LLM (JSON):**
```json
{
  "action": "reply | confirm_order | request_human | cancel_order | update_client",
  "message": "Texto para el cliente",
  "data": {}
}
```

---

## notificaciones.json

Envía mensajes de WhatsApp al cambiar el estado de un pedido.

**Trigger:** `POST /webhook/notificacion-pedido`

**Payload esperado:**
```json
{
  "order_id": 7,
  "new_status": "in_delivery",
  "customer_phone": "5491112345678",
  "session_name": "pizzeria-norte",
  "delivery_type": "delivery",
  "credit_amount": 0,
  "payment_link": ""
}
```

**Campos opcionales del payload:**

| Campo | Cuándo incluirlo |
|---|---|
| `delivery_type` | `"delivery"` o `"pickup"` — requerido para `ready_for_dispatch` |
| `credit_amount` | Monto de crédito acreditado — incluir cuando `new_status = "cancelled"` con crédito |
| `payment_link` | URL de MercadoPago — incluir cuando `new_status = "pending_payment"` con pago online |

**Estados con notificación al cliente:**

| Estado | Mensaje |
|---|---|
| `pending_payment` (sin link) | "Tu pedido #X fue recibido. ¡Estamos en eso!" |
| `pending_payment` (con link MP) | "Tu pedido #X fue recibido. Para pagar usá: [link]" |
| `pending_preparation` | "Tu pedido #X fue recibido. ¡Estamos en eso!" |
| `in_preparation` | "¡Tu pedido #X está siendo preparado! 👨‍🍳" |
| `ready_for_dispatch` (delivery) | "Tu pedido listo y ya salió para entregarte. ¡En camino! 📦" |
| `ready_for_dispatch` (pickup) | "¡Tu pedido listo para retirar! Te esperamos. 📦" |
| `in_delivery` | "Tu pedido está en camino. ¡Ya llega! 🛵" |
| `delivered` | "¡Tu pedido fue entregado! Gracias por elegirnos. 🎉" |
| `cancelled` (sin crédito) | "Tu pedido fue cancelado. No se realizó ningún cobro. ❌" |
| `cancelled` (con crédito) | "Tu pedido fue cancelado. Tenés un crédito de $X. ❌" |
| `with_incident` | "Inconveniente con tu pedido. Estamos resolviéndolo. ⚠️" |

---

## inactividad-timer.json

Cierra sesiones de chat inactivas en dos fases según la especificación §5.6.

**Trigger:** cron cada 5 minutos

**Comportamiento de dos fases:**

| Inactividad | Acción |
|---|---|
| 10–14 minutos | Envía recordatorio: "¿Seguís ahí? Tu sesión cierra en unos minutos." |
| ≥ 15 minutos | Cierra la sesión + descarta el pedido activo + notifica al cliente |

**Reglas:**
- Solo aplica a sesiones con `status = active` (excluye `waiting_human` y `transferred_human`)
- El pedido en curso (`in_progress`) se descarta automáticamente al cerrar la sesión
- No aplica a pedidos ya confirmados (cualquier estado posterior a `in_progress`)

**Parámetro requerido en la API** `GET /conversaciones/inactivas`:
- `minutos_inactiva=10` — mínimo minutos de inactividad
- `status=active` — excluye sesiones HITL
- `include_hitl=false` — excluye explícitamente sesiones derivadas

La respuesta debe incluir `last_message_at` (o `updated_at`) y `active_order_id` para que el flujo pueda clasificar y descartar pedidos correctamente.

---

| Archivo | Descripción |
|---------|-------------|
| `chatbot-principal.json` | Chatbot LLM con contexto completo y soporte HITL |
| `notificaciones.json` | Notificaciones de estado de pedido (todos los casos del §5.7) |
| `inactividad-timer.json` | Cierre automático por inactividad en dos fases (§5.6) |
