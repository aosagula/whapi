# Flujos n8n — Pizzería Chatbot

Importá cada archivo JSON desde **n8n → Workflows → Import from file**.

## Variables de entorno requeridas en n8n

Configurá en **Settings → Variables**:

| Variable | Ejemplo |
|---|---|
| `API_BASE_URL` | `http://backend:8000` |
| `WPPCONNECT_BASE_URL` | `http://wppconnect:21465` |
| `WPPCONNECT_SECRET_KEY` | (secret key de WPPConnect) |

Para el nodo LLM, configurá la credencial **OpenAI API** en n8n.

---

## chatbot-principal.json

Procesa mensajes entrantes y genera respuestas con LLM.

**Trigger:** `POST /webhook/chatbot-mensaje`

**Payload esperado:**
```json
{
  "pizzeria_id": 1,
  "session_id": 42,
  "status": "active",
  "message": "Quiero pedir una pizza"
}
```

**Flujo:**
1. Si la sesión está en `transferred_human` → ignora (HITL activo)
2. Obtiene contexto de la sesión desde la API
3. Llama al LLM con el historial completo
4. Guarda la respuesta (que la envía por WPPConnect)

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
  "session_name": "pizzeria-norte"
}
```

**Estados con notificación:**
`pending_preparation` · `in_preparation` · `ready_for_dispatch` · `in_delivery` · `delivered` · `cancelled`

---

## inactividad-timer.json

Cierra sesiones de chat inactivas enviando un recordatorio previo.

**Trigger:** cron cada 5 minutos

**Comportamiento:**
1. Consulta sesiones `active` con más de 30 min de inactividad
2. Envía recordatorio por WPPConnect
3. Cierra la sesión via API

| Archivo | Descripción |
|---------|-------------|
| `chatbot-principal.json` | Chatbot LLM con soporte HITL |
| `notificaciones.json` | Notificaciones de estado de pedido |
| `inactividad-timer.json` | Cierre automático por inactividad |
