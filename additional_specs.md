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
