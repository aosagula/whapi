# Flows de n8n — Whapi Chatbot

Arquitectura multi-agente para el chatbot de WhatsApp. El **Orquestador** recibe cada mensaje entrante y decide qué agente especializado invocar según el contexto.

## Arquitectura

```
WPPConnect Webhook
      │
      ▼
chatbot-principal  ──► Orquestador (GPT-4o + memoria conversacional)
                              │
                              ├──► [AI Agent] agente-catalogo   (consultas de menú)
                              ├──► [AI Agent] agente-pedido     (carrito + confirmación)
                              ├──► [HTTP]     actualizar_cliente (nombre, dirección)
                              ├──► [HTTP]     procesar_pago      (MP, efectivo, transferencia)
                              └──► [HTTP]     derivar_humano     (HITL)

notificaciones     ──► Webhook del backend → mensaje directo al cliente (sin LLM)
timer-inactividad  ──► Cron cada 2 min → GPT-4o mini → mensaje de consulta
```

## Orden de importación

1. `agente-catalogo.json`
2. `agente-pedido.json`
3. `notificaciones.json`
4. `timer-inactividad.json`
5. `chatbot-principal.json` ← importar último (necesita los IDs de los anteriores)

## Variables de entorno en n8n

Ir a **Settings → Variables** y crear:

| Variable | Valor | Descripción |
|---|---|---|
| `WHAPI_BACKEND_URL` | `http://host:8000` | URL del backend FastAPI (sin / final) |
| `WHAPI_N8N_API_KEY` | `eyJhbGci...` | Valor de `N8N_API_KEY` del `.env` del backend |
| `WPPCONNECT_HOST` | `https://wppconnect.ejemplo.com` | URL de WPPConnect (sin / final) |

## Credenciales en n8n

Crear una credencial **OpenAI API** en n8n con tu `OPENAI_API_KEY` y tomar nota de su ID.

## Pasos post-importación

### 1. Configurar IDs de credencial OpenAI

En cada flow que use OpenAI, editar el nodo del modelo y seleccionar la credencial creada:
- `chatbot-principal` → nodo **GPT-4o Orquestador**
- `agente-catalogo` → nodo **GPT-4o Catálogo**
- `agente-pedido` → nodo **GPT-4o Pedido**
- `timer-inactividad` → nodo **Redactar Mensaje de Consulta**

### 2. Vincular agentes como tools en el Orquestador

En `chatbot-principal`, editar los nodos de tool:
- **consultar_catalogo**: seleccionar el workflow "Whapi — Agente Catálogo"
- **gestionar_pedido**: seleccionar el workflow "Whapi — Agente Pedido"

### 3. Configurar el webhook de WPPConnect

En la instancia de WPPConnect, configurar el webhook de mensajes entrantes apuntando a la URL del flow `chatbot-principal`:

```
POST https://n8n.ejemplo.com/webhook/whapi-chatbot
```

### 4. Configurar el webhook de notificaciones en el backend

En el `.env` del backend agregar:

```
N8N_NOTIFICACIONES_WEBHOOK=https://n8n.ejemplo.com/webhook/whapi-notificacion
```

Y asegurarse de que el servicio de notificaciones del backend llame a este webhook cuando cambia el estado de un pedido.

### 5. Activar los flows

Activar en este orden:
1. `agente-catalogo`
2. `agente-pedido`
3. `chatbot-principal`
4. `notificaciones`
5. `timer-inactividad`

## Notas de diseño

- **Memoria**: El orquestador usa Window Buffer Memory keyed por `session_id` — cada cliente tiene su propia memoria conversacional.
- **Agentes especializados**: `agente-catalogo` y `agente-pedido` son stateless — toda la persistencia va a la DB via el backend.
- **Sin LLM**: El flow de notificaciones envía mensajes formateados sin pasar por LLM (más rápido y predecible).
- **Timer de inactividad**: Corre cada 2 minutos y consulta el backend por sesiones con último mensaje > 10 min. Usa GPT-4o mini (más económico) solo para redactar el mensaje de consulta.
- **HITL**: Cuando el orquestador llama `derivar_humano`, la sesión pasa a `waiting_operator` y el bot deja de responder. El operador atiende desde el panel web.
