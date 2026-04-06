# Especificaciones adicionales

Decisiones de diseño e implementaciones que no estaban en la spec original (`docs/especificacion-chatbot-pizzeria.md`).

---

## Fase 4 — Catálogo

### Slots abiertos en combos
Los ítems de un combo pueden ser **abiertos** (el cliente elige el producto de una categoría, en lugar de tener un producto fijo). Campos agregados al modelo `ComboItem`:
- `is_open: bool` — si es true, el slot no tiene producto fijo
- `open_category: ProductCategory | null` — categoría disponible para elegir (pizza / empanada / drink)

Regla: un ítem de combo es abierto XOR tiene `product_id`. Ambos no pueden ser nulos/presentes al mismo tiempo.

---

## Fase 5 — Tablero de pedidos

### Número de pedido visible (`order_number`)
Se agregó el campo `order_number` (entero secuencial por comercio) a la tabla `orders`. Se gestiona a nivel aplicación: al crear un pedido se obtiene el máximo actual del comercio y se suma 1. No usa secuencias de DB para mantener compatibilidad con la migración incremental.

### Historial de estados (`order_status_history`)
Tabla nueva que registra cada transición de estado con: estado anterior, estado nuevo, usuario que lo cambió, timestamp y nota opcional. Se crea una entrada automáticamente al crear el pedido y en cada cambio de estado.

### Notas internas (`internal_notes`)
Campo de texto libre en `orders`, solo visible para el personal del comercio. Editable desde el panel en cualquier estado del pedido.

### Repartidor asignado (`delivery_person_id`)
FK nullable a `users` en la tabla `orders`. Solo los roles cajero/admin/owner pueden asignar repartidor. Se valida que el usuario pertenezca al comercio.

### Política de cancelación automática
Al cancelar desde el panel, la política de pago se calcula automáticamente:
- Pedido no pagado → `no_charge`
- Pedido pagado en estado `pending_preparation` o `in_preparation` → `credit` (acredita el total al saldo del cliente)
- El cajero puede opcionalmente sobreescribir con `payment_policy` explícito

### Visibilidad por rol en el tablero
- **Cocinero**: ve solo pedidos en `pending_preparation` e `in_preparation`
- **Repartidor**: ve solo pedidos en `to_dispatch`, `in_delivery` y `with_incident`
- **Cajero/Admin/Owner**: ven todos los estados

### Rol guardado en localStorage
Al seleccionar un comercio desde `/selector`, se guarda `comercio_role` en localStorage además de `comercio_id` y `comercio_name`. La página de pedidos lo usa para determinar las acciones disponibles.

### Endpoint básico de clientes (adelanto de Fase 7)
Se creó `POST /comercios/{id}/clientes` y `GET /comercios/{id}/clientes/{cliente_id}` como endpoints mínimos para soportar la creación de pedidos manuales y los tests de la Fase 5. El ABM completo se implementa en Fase 7.

---

## Fase 6 — Pedidos manuales

### Campo `has_whatsapp` en Customer
Se agregó el campo `has_whatsapp: bool` (default `true`) al modelo `Customer`. Indica si el cliente tiene WhatsApp activo. Cuando es `false`:
- No se envían notificaciones automáticas de estado por WhatsApp.
- El formulario de pedido manual advierte al operador.
- Migración: `a0a5b0bdb649_agregar_has_whatsapp_a_customer.py`.

### Endpoints de clientes extendidos (Fase 6)
Se completaron los endpoints de clientes necesarios para el formulario de pedido manual:
- `GET /comercios/{id}/clientes/buscar?phone=...` — búsqueda por teléfono (devuelve 404 si no existe)
- `PATCH /comercios/{id}/clientes/{cliente_id}` — actualizar nombre, dirección y has_whatsapp

### Formulario wizard de pedido manual
El formulario usa 5 pasos en secuencia:
1. **Cliente**: búsqueda por teléfono → cliente encontrado (continuar) o no encontrado (formulario de alta inline)
2. **Pedido**: catálogo con tabs por categoría (pizza / empanada / bebida / combo), carrito con cantidad y precio
3. **Entrega**: delivery (con dirección) o retiro en local; sugiere la dirección guardada del cliente
4. **Pago**: efectivo (→ `cash_on_delivery`) / transferencia / MercadoPago (→ `pending_payment`)
5. **Confirmar**: resumen completo, botón "Confirmar pedido"

Al confirmar se llama `POST /comercios/{id}/pedidos` con `origin: "phone"`.

### Pre-carga de dirección del cliente
Si el cliente ya tiene dirección guardada, se pre-carga automáticamente en el paso de entrega. El operador puede usar la guardada o sobreescribir.

### Estado inicial de pedidos telefónicos: `in_preparation`
Los pedidos creados con `origin: "phone"` se crean directamente en estado `in_preparation`, saltando `pending_preparation`. Razón: el operador que toma el llamado ya actúa como "aceptador" del pedido. El historial registra la entrada con la nota "Pedido telefónico — en preparación". Los pedidos `operator` o `whatsapp` siguen entrando en `pending_preparation`.

### Notas de preparación y entrega en pedidos
Se agregaron dos campos opcionales al modelo `Order`:
- `kitchen_notes: TEXT nullable` — instrucciones para la cocina (alergias, especificaciones). Se carga en el paso 2 del wizard.
- `delivery_notes: TEXT nullable` — instrucciones para el repartidor (timbre, piso, referencia). Se carga en el paso 3 del wizard.

Ambos campos se muestran en el resumen del paso 5 (confirmación) y en el panel de detalle del pedido en el kanban (amber para cocina, azul para entrega). Son de solo lectura en el detalle — se definen al crear el pedido. Migración: `0003_agregar_notas_cocina_entrega.py`.

---

## Fase 7 — Clientes y créditos

### Listado de clientes con búsqueda
El endpoint `GET /comercios/{id}/clientes` soporta:
- Paginación con `page` y `page_size` (máx. 100)
- Búsqueda case-insensitive por nombre o teléfono con el parámetro `q`
- Orden por fecha de alta descendente

### Historial de pedidos del cliente
`GET /comercios/{id}/clientes/{cliente_id}/pedidos` devuelve todos los pedidos del cliente en ese comercio, ordenados por fecha descendente. El detalle de cada pedido incluye: número, estado, estado de pago, origen, tipo de entrega, total y fecha.

### Ajuste manual de crédito
`POST /comercios/{id}/clientes/{cliente_id}/creditos` permite al Admin/Dueño registrar ajustes manuales de crédito:
- Monto positivo → acredita saldo al cliente
- Monto negativo → descuenta saldo (falla con 422 si el resultado sería negativo)
- Campo `reason` opcional para registrar el motivo
- Actualiza `credit_balance` en el registro del cliente atómicamente
- Solo roles `owner` y `admin` pueden ejecutarlo (cajero recibe 403)

### Historial de movimientos de crédito
`GET /comercios/{id}/clientes/{cliente_id}/creditos` devuelve todos los movimientos de crédito del cliente, ordenados por fecha descendente. Cada movimiento incluye: monto (con signo), motivo, pedido vinculado (si aplica) y timestamp.

### Edición inline en detalle de cliente
El panel de detalle permite editar nombre y dirección directamente con un click en el ícono de edición (pencil). El campo se convierte en un input con botones Confirmar (Enter) y Cancelar (Escape). El cambio se persiste con `PATCH /clientes/{id}`.

### Navegación al detalle desde listado
Al hacer click en una fila del listado de clientes se navega a `/{comercio_id}/clientes/{cliente_id}`. El detalle incluye botón "Volver al listado" (con aria-label) para regresar.

### Acceso al ajuste de crédito según rol
El botón "Ajustar" crédito en el detalle solo se muestra para roles `owner` y `admin`. El rol se lee de `localStorage.comercio_role` (seteado al seleccionar el comercio). El cajero ve el saldo pero no puede modificarlo.

---

## Fase 8 — Conversaciones activas (HITL)

### Roles con acceso al panel de conversaciones
`ROLES_HITL = {"owner", "admin", "cashier"}`. Cocinero y repartidor reciben 403. La restricción aplica a todos los endpoints del módulo conversaciones.

### Estados de sesión visibles en el listado
El listado `/comercios/{id}/conversaciones` devuelve únicamente sesiones en `waiting_operator` o `assigned_human`. Las sesiones `closed` y `active_bot` no aparecen.

### Ordenamiento del listado
Las sesiones se ordenan por `created_at` ascendente (las más antiguas primero) para priorizar la atención de los clientes que llevan más tiempo esperando.

### Campo `wait_seconds` en el listado
Cada sesión del listado incluye `wait_seconds`, calculado como la diferencia en segundos entre `now()` y `created_at`. Permite mostrar cuánto tiempo lleva esperando el cliente sin que el frontend haga cálculos de fechas.

### Transición `atender` (waiting_operator → assigned_human)
Solo válida si la sesión está en `waiting_operator`. Devuelve 409 si ya está asignada u otro estado. Asigna `assigned_operator_id` y `assigned_operator_name` con los datos del usuario autenticado.

### Envío de mensajes del operador
`POST .../mensaje` solo funciona en estado `assigned_human`. Devuelve 409 si la sesión no está asignada. Un mensaje vacío o con solo espacios devuelve 422. El mensaje se guarda con `direction="outbound"` en la tabla `Message`.

### Devolución al bot (assigned_human → active_bot)
`POST .../devolver-al-bot` limpia `assigned_operator_id` y `assigned_operator_name`. Solo válido en `assigned_human`; devuelve 409 en cualquier otro estado.

### Cierre sin pedido (assigned_human → closed)
`POST .../cerrar` cierra la sesión y descarta el pedido en curso (si existe) cambiando su estado a `discarded`. Solo válido en `assigned_human`. La sesión cerrada desaparece del listado.

### Detección del pedido en curso en el detalle
El helper `_cargar_pedido_en_curso` busca un `Order` asociado a la sesión con estado distinto de `delivered`, `cancelled` y `discarded`. Si hay un pedido activo, se incluye en la respuesta con sus ítems y datos de entrega.

### Auto-refresco del listado
El listado de conversaciones se refresca automáticamente cada 10 segundos via `setInterval`. También hay un botón "Actualizar" manual para forzar la recarga.

### Layout split en el detalle de conversación
El detalle usa un layout de dos columnas: panel izquierdo flexible (historial de chat + input) y panel derecho fijo de 288px (pedido en curso, datos del cliente, acciones del operador). Las acciones (Devolver al bot, Cerrar sin pedido) solo aparecen cuando `status === "assigned_human"`.

### Separador "Operador conectado"
Cuando la sesión pasa a `assigned_human`, se muestra un separador visual en el chat con el texto "— Operador conectado —" para indicar el punto desde el cual el humano toma control.

---

## Mejoras transversales — Página de Pedidos (sin fase asignada)

### Tabs de vista (General / Cocina / Delivery)
La página de pedidos agrega un sistema de tres tabs:

- **General**: la tabla existente con todos los filtros (estado, pago, búsqueda, paginación).
- **Cocina** (`VistaCocina`): muestra solo pedidos en `pending_preparation` e `in_preparation`, agrupados por estado, en grilla de tarjetas. Cada tarjeta muestra: nº de pedido, hora, tipo de entrega e ítems. Incluye botón de avance rápido al siguiente estado (habilitado para roles `cook`, `cashier`, `admin`, `owner`). Clic en la tarjeta abre el panel de detalle lateral.
- **Delivery** (`VistaDelivery`): muestra solo pedidos en `to_dispatch` e `in_delivery`, agrupados por estado, en grilla de tarjetas. Cada tarjeta muestra: nº de pedido, hora, nombre del cliente, teléfono, tipo de entrega e ítems resumidos. La dirección completa se consulta en el panel de detalle. Incluye botón de avance rápido (habilitado para roles `delivery`, `cashier`, `admin`, `owner`).

Ambas vistas cargan con `page_size: 50` y un botón de refresh. El panel de detalle lateral es accesible desde las tres vistas.

### Dashboard de contadores por estado
Encima de los tabs se muestra una fila de chips con el conteo en tiempo real de pedidos activos por estado: `pending_preparation`, `in_preparation`, `to_dispatch`, `in_delivery` y `with_incident`. Los conteos se obtienen haciendo llamadas paralelas al endpoint de listado con `page_size=1` y leyendo el campo `total`. Se actualizan al montar la página y al cambiar el estado de un pedido desde la vista General.

Los contadores se muestran como tarjetas en una grilla de 5 columnas (`grid-cols-5`), con número grande (`text-4xl font-bold`) y etiqueta debajo, distribuyéndose uniformemente a lo ancho de la pantalla.

---

## Fase 9 — Gestión de números de WhatsApp

### Modelo `WhatsappNumber` — campo `label`
Se agregó el campo `label: String(100) nullable` al modelo `WhatsappNumber` para que el owner/admin pueda identificar cada número con un nombre descriptivo (ej: "Número principal", "Zona Norte"). Migración: `b504cb07262e_agregar_label_a_whatsapp_numbers`.

### Acceso restringido a owner y admin
Todos los endpoints del módulo WhatsApp (`GET/POST/PATCH/DELETE /comercios/{id}/whatsapp`) requieren rol `owner` o `admin` (via `get_membresia_gestion`). Cajero, cocinero y repartidor reciben 403.

### Integración WPPConnect — modo graceful sin servidor
Si `WPPCONNECT_HOST` está vacío (no configurado), todas las operaciones WPPConnect son no-ops. El número se crea igualmente en la DB con estado `scanning`. Esto permite usar y testear la UI sin servidor WPPConnect activo.

### Flujo de conexión de un número
1. El owner ingresa el número y una etiqueta opcional → POST crea el registro en DB con `status="scanning"` e inicia sesión en WPPConnect.
2. Automáticamente se abre el modal QR que hace polling cada 5 segundos al endpoint `GET .../qr`.
3. Cuando WPPConnect reporta `connected`, el modal muestra confirmación y se cierra automáticamente.

### Eliminación (soft delete)
`DELETE` no borra el registro; lo marca con `is_active=False` y `status="disconnected"`. Las conversaciones históricas asociadas al número se conservan.

### Reconexión
`POST .../reconectar` reinicia la sesión WPPConnect y devuelve un nuevo QR. Usado cuando un número queda en estado `disconnected`.

### Edición inline de etiqueta
En la tabla de números, el botón de edición convierte la celda de etiqueta en un input inline (confirmación con Enter o botón ✓, cancelación con Escape o botón ✗).

### Alerta de números desconectados
Si hay uno o más números activos con `status="disconnected"`, se muestra un banner de advertencia en la parte superior de la página indicando cuántos números necesitan reconexión.

---

## Fase 10 — Webhooks, pagos y notificaciones

### Notificaciones automáticas al cliente
Las notificaciones se envían via WPPConnect al cambiar el estado de un pedido o al cancelarlo. El servicio `services/notificaciones.py` centraliza los mensajes por evento (tabla completa en spec sección 5.7). Usa el primer número `connected` del comercio como sesión emisora. Si WPPConnect no está configurado o falla, la notificación se loguea y se omite sin bloquear la operación.

### Hook de notificaciones en pedidos
Las funciones `notificar_cambio_estado` y `notificar_cancelacion` se llaman al final de `cambiar_estado` y `cancelar_pedido` en `services/pedidos.py`. Son fire-and-forget: los errores de envío no propagan excepción.

### Integración MercadoPago — modo graceful sin token
Si `MERCADOPAGO_ACCESS_TOKEN` está vacío, `crear_preferencia` devuelve un link simulado (`https://mp.example.com/pay/{order_id}`). Permite usar y testear la UI sin cuenta de MP configurada.

### Webhook WPPConnect — routing por número destino
`POST /webhooks/wppconnect` identifica el tenant buscando el campo `to` del payload en la tabla `whatsapp_numbers`. Si el número no está registrado, responde `{"ok": true, "skipped": true}`. Si el cliente no existe, lo crea como anónimo. Guarda el mensaje entrante en la sesión activa del cliente (o crea una nueva sesión `active_bot`). No requiere JWT.

### Webhook MercadoPago — IPN
`POST /webhooks/mercadopago` acepta notificaciones de tipo `payment`. Verifica el estado del pago con la API de MP. Si está `approved`, actualiza `payment_status → paid` en el pedido y notifica al cliente. Implementa idempotencia: si el pedido ya está pagado, ignora la notificación. No requiere JWT.

### Endpoint pago-link
`POST /comercios/{id}/pedidos/{pedido_id}/pago-link` genera una preferencia MP y devuelve `{ preference_id, init_point, sandbox_init_point }`. Solo disponible para `owner` y `admin` cuando `payment_status === "pending_payment"`. También envía el link al cliente via WhatsApp automáticamente.

### Botón "Link de pago" en PedidoDetalle
Visible para `owner` y `admin` cuando `payment_status === "pending_payment"`. Al hacer clic genera el link de MP y lo muestra con un botón de "Copiar" que confirma visualmente la acción (ícono de check por 2 segundos).

---

## Fase 11 — Arquitectura multi-agente n8n

### Patrón Orquestador + Agentes especializados

La especificación original planteaba n8n como un orquestador simple con un único LLM. Se decidió implementar una arquitectura de múltiples agentes:

- **Orquestador** (`chatbot-principal`): AI Agent GPT-4o con memoria conversacional (Window Buffer Memory keyed por session_id). Decide qué agente invocar según el contexto.
- **Agente Catálogo** (`agente-catalogo`): AI Agent especializado, stateless. Herramientas: `obtener_catalogo`.
- **Agente Pedido** (`agente-pedido`): AI Agent especializado, stateless. Herramientas: `crear_pedido`, `ver_carrito`, `agregar_item`, `quitar_item`, `confirmar_pedido`.
- **Herramientas simples** (sin LLM, directamente en el orquestador): `actualizar_cliente`, `procesar_pago`, `derivar_humano`.

### Router interno `/n8n/` en el backend

Se agregó un nuevo router FastAPI con autenticación por API key (`X-N8N-Api-Key`), sin JWT de usuario. Expone 14 endpoints exclusivamente para uso interno de n8n:

- `GET /n8n/resolver-tenant` — identifica el comercio por número WhatsApp destino
- `GET /n8n/comercios/{id}/contexto` — contexto completo del turno (crea cliente y sesión si no existen)
- `POST /n8n/comercios/{id}/mensajes` — persiste mensajes en el historial
- `POST /n8n/comercios/{id}/clientes/buscar-o-crear`
- `PATCH /n8n/clientes/{id}`
- `GET /n8n/comercios/{id}/catalogo`
- `POST /n8n/comercios/{id}/pedidos`
- `POST /n8n/comercios/{id}/pedidos/{id}/items`
- `DELETE /n8n/comercios/{id}/pedidos/{id}/items/{item_id}`
- `GET /n8n/comercios/{id}/pedidos/{id}/resumen`
- `POST /n8n/comercios/{id}/pedidos/{id}/confirmar`
- `POST /n8n/comercios/{id}/pedidos/{id}/pago`
- `POST /n8n/conversaciones/{id}/derivar`
- `GET /n8n/sesiones/inactivas`

### Flujo de confirmación y pago

1. El `agente-pedido` gestiona el carrito y la confirmación (in_progress → pending_payment).
2. El orquestador detecta el resultado `PEDIDO_CONFIRMADO` del agente y llama directamente la herramienta `procesar_pago`.
3. `procesar_pago` (HTTP tool, sin LLM) registra el método y genera el link de MercadoPago si aplica.

### Variables de entorno agregadas

- `N8N_API_KEY`: clave interna de autenticación para los endpoints `/n8n/`
