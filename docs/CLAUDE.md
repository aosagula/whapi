# CLAUDE.md — Reglas del Proyecto: Whapi (Plataforma Multi-Tenant de Chatbot para Comercios)

## Regla de oro
Antes de escribir cualquier código, presentá el plan de implementación del paso actual y esperá confirmación.

---

## Flujo de trabajo obligatorio

1. **Planificá primero**: mostrá qué vas a hacer y cómo, esperá confirmación antes de ejecutar.
2. **Commit antes de cambios grandes**: refactors, cambios de schema, inicio de nuevo módulo → `git add -A && git commit -m "..."` primero.
3. **Un módulo a la vez**: no avancés al siguiente hasta que el actual esté funcionando y verificado.
4. **Consultá la spec ante cualquier duda**: `docs/especificacion-chatbot-pizzeria.md`.

---

## Stack tecnológico

| Componente        | Tecnología                                         |
|-------------------|----------------------------------------------------|
| API principal     | FastAPI (Python 3.12+)                             |
| Base de datos     | PostgreSQL 16 (instancia existente, sin schema)    |
| ORM               | SQLAlchemy 2.x + Alembic (migraciones)             |
| Panel web         | Next.js 14 (App Router) + TypeScript               |
| UI components     | shadcn/ui + Tailwind CSS                           |
| Bridge WhatsApp   | WPPConnect Server (ya corriendo, solo consumir)    |
| Orquestador       | n8n (instalado, flujos se crean en Fase 10)        |
| Infraestructura   | Docker Compose solo para backend y frontend        |

---

## Infraestructura existente — NO recrear

| Servicio          | Estado       | Qué hacer                                                       |
|-------------------|--------------|-----------------------------------------------------------------|
| WPPConnect Server | ✅ Corriendo | Consumir su API / recibir webhooks. Gestiona múltiples sesiones.|
| PostgreSQL        | ✅ Corriendo | Instancia vacía. Alembic crea todo el schema.                   |
| n8n               | ✅ Instalado | Sin flujos. Se crean en Fase 10 como JSON importables.          |

---

## Nombre del producto

El producto se llama **Whapi**. Este nombre aparece en la landing page, en el título del navegador, en los emails, y en toda comunicación hacia el usuario.

---

## ⚠️ Arquitectura Multi-Tenant

Cada **comercio** es un tenant aislado. Todo query operativo filtra siempre por `comercio_id`. Sin excepciones.

```
Cuenta (Dueño)
  └── Comercio A  ←── tenant
  │     ├── TelefonoWhatsApp (1..N sesiones WPPConnect)
  │     ├── Empleados asociados (con roles)
  │     ├── Catálogo propio
  │     └── Pedidos y clientes propios
  └── Comercio B  ←── tenant separado
```

---

## Modelo de usuarios y asociación a comercios

### Tipos de usuario en el registro

| Tipo          | Descripción                                                        |
|---------------|--------------------------------------------------------------------|
| **Dueño**     | Crea su cuenta y da de alta uno o más comercios. Al crear un comercio queda automáticamente asociado a él con rol `dueño`. |
| **Empleado**  | Se registra como colaborador. Puede estar asociado a varios comercios. Solo accede a los comercios donde un Dueño lo haya asociado. |

### Reglas de asociación

- Al crear un comercio, el Dueño queda asociado automáticamente.
- El Dueño puede asociar empleados a su comercio, asignándoles un rol.
- Un empleado puede estar asociado a múltiples comercios (de distintos dueños).
- El Dueño puede dar de baja a un empleado de su comercio (desasocia, no elimina la cuenta).
- Si un usuario no está asociado a ningún comercio, el sistema no le muestra nada después del login.

### Roles dentro de un comercio

| Rol           | Permisos                                                          |
|---------------|-------------------------------------------------------------------|
| `dueño`       | Acceso completo. Gestiona comercios, empleados y configuración.   |
| `admin`       | Acceso operativo completo a su comercio. Gestiona empleados.      |
| `cajero`      | Ve pedidos, gestiona pagos, crea pedidos telefónicos, atiende HITL.|
| `cocinero`    | Ve pedidos en preparación únicamente.                             |
| `repartidor`  | Ve pedidos para despachar/entregar.                               |

---

## Estructura de navegación — Panel web

### Landing page (pública, sin login)
- Página de presentación de **Whapi**.
- Muestra características y beneficios para el dueño de un comercio gastronómico.
- Botón **Iniciar sesión** en la esquina superior derecha → lleva al login.
- Botón **Registrarse** en la landing → lleva al registro.

### Flujo de acceso
```
Landing (/)
  ├── [Iniciar sesión] → /login
  │     └── Credenciales correctas → Selector de comercios (/selector)
  │           ├── Tiene comercios asociados → muestra lista → entra al comercio
  │           └── Sin comercios asociados → mensaje informativo, sin acceso
  └── [Registrarse] → /registro
        ├── Opción A: Soy dueño de un comercio → registro de cuenta + alta de primer comercio
        └── Opción B: Soy empleado / colaborador → solo registro de cuenta (accede cuando un dueño lo asocie)
```

### Sidebar de navegación (panel autenticado)

La barra lateral está siempre visible en el lado izquierdo. Es colapsable:

| Estado      | Comportamiento                                                      |
|-------------|---------------------------------------------------------------------|
| **Expandido**  | Muestra icono + nombre de cada ítem del menú                     |
| **Minimizado** | Muestra solo iconos. Al hacer hover → tooltip con el nombre      |

**Ítems del menú principal:**

```
📦 Pedidos
📞 Pedidos manuales
👥 Clientes
⚙️  Ajustes
    ├── 🔐 Permisos
    ├── 👤 Empleados
    ├── 🍕 Productos
    └── 🎁 Combos
📊 Reportes
    └── [reportes del comercio activo]
```

**Usuario autenticado (esquina inferior izquierda del sidebar):**
- Muestra avatar + nombre del usuario (cuando expandido) o solo avatar (cuando minimizado).
- Al hacer clic → menú desplegable con:
  - Editar perfil
  - Cerrar sesión

### Selector de comercios (post-login)
- Se muestra después del login si el usuario tiene más de un comercio asociado.
- Lista todos los comercios del usuario con nombre, estado de pedidos activos.
- El usuario selecciona uno y entra a su dashboard.
- Puede cambiar de comercio desde el menú principal sin cerrar sesión.

---

## Estructura del proyecto

```
whapi/
├── docker-compose.yml
├── .env.example
├── docs/
│   └── especificacion-chatbot-pizzeria.md
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py          # Login, registro, JWT
│   │   │   ├── comercios.py     # ABM de comercios
│   │   │   ├── empleados.py     # Asociación empleado-comercio, roles
│   │   │   ├── webhooks.py      # WPPConnect + MercadoPago
│   │   │   ├── pedidos.py
│   │   │   ├── clientes.py
│   │   │   ├── catalogo.py
│   │   │   ├── whatsapp.py      # Gestión de números/sesiones
│   │   │   └── reportes.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── db.py
│   │   │   ├── auth.py
│   │   │   └── tenant.py        # Middleware de aislamiento por comercio
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   └── Dockerfile
└── frontend/
    ├── app/
    │   ├── page.tsx             # Landing page (/)
    │   ├── login/               # /login
    │   ├── registro/            # /registro (bifurcado: dueño / empleado)
    │   ├── selector/            # /selector (elegir comercio post-login)
    │   └── [comercio]/          # Panel operativo (scope del comercio activo)
    │       ├── pedidos/
    │       ├── pedidos-manuales/
    │       ├── clientes/
    │       ├── ajustes/
    │       │   ├── permisos/
    │       │   ├── empleados/
    │       │   ├── productos/
    │       │   └── combos/
    │       └── reportes/
    ├── components/
    │   ├── layout/
    │   │   ├── Sidebar.tsx      # Colapsable, con tooltips en modo minimizado
    │   │   ├── UserMenu.tsx     # Avatar + menú inferior del sidebar
    │   │   └── ComercioSwitcher.tsx
    │   └── ...
    ├── lib/
    └── Dockerfile
```

---

## Convenciones de código

### Python (FastAPI)
- Tipado estricto: `from __future__ import annotations`
- Nunca hardcodear valores
- Un router por dominio
- Todos los endpoints operativos reciben `comercio_id` del contexto autenticado
- Docstrings en español

### TypeScript (Next.js)
- Strict mode activado
- Componentes en PascalCase
- Server Components por defecto; Client Components solo cuando sea necesario
- Nunca usar `any`

### Base de datos
- Migraciones siempre con Alembic
- Todas las tablas operativas tienen `comercio_id` como FK no nula
- Soft delete para productos y pedidos (`disponible`, `activo`)
- Timestamps en UTC

---

## Variables de entorno

```
DATABASE_URL=postgresql://user:pass@host:5432/whapi
SECRET_KEY=
ACCESS_TOKEN_EXPIRE_MINUTES=60
WPPCONNECT_BASE_URL=
WPPCONNECT_SECRET_KEY=
N8N_WEBHOOK_BASE_URL=
MERCADOPAGO_ACCESS_TOKEN=
OPENAI_API_KEY=
```

---

## Git

- Mensajes en español, en infinitivo
- Commit antes de: cambios de schema, refactors, inicio de módulo nuevo
- Nunca commitear `.env`, `__pycache__`, `node_modules`, `.next`

---

## Reglas de negocio críticas

1. **Aislamiento de tenant**: Todo query operativo filtra por `comercio_id`. Sin excepciones.
2. **Cliente scoped a comercio**: Mismo teléfono = clientes distintos en distintos comercios.
3. **Asociación automática**: Al crear un comercio, el Dueño queda asociado automáticamente con rol `dueño`.
4. **Sin comercios → sin acceso**: Un usuario sin comercios asociados no puede operar.
5. **WPPConnect multi-sesión**: Cada `TelefonoWhatsApp` tiene su propia sesión. El webhook entrante identifica el comercio por el número destino.
6. **Crédito**: Asociado al cliente en ese comercio. No transferible.
7. **Mitad y mitad**: Precio = mayor de los dos gustos + recargo configurable por comercio.
8. **Cancelaciones**: Ver spec sección 6.4. No eliminar, solo cambiar estado.
9. **Productos**: Nunca eliminar físicamente si tienen pedidos históricos. Solo `disponible = false`.
10. **Código de producto**: Inmutable. Único dentro del comercio.
11. **Origen del pedido**: Siempre registrar: `whatsapp` / `telefonico` / `operador`.
12. **HITL**: LLM suspendido en estado `derivada_humano`.

---

## ✅ Protocolo de Checkpoint — OBLIGATORIO al final de cada fase

Antes de hacer el commit de cualquier fase:

1. **Releé** las secciones de la spec y las definiciones de UX/navegación de `CLAUDE.md` correspondientes a esta fase.
2. **Generá** el checklist con cada funcionalidad, regla de negocio, comportamiento de UI y caso borde definidos.
3. **Verificá** el código: ✅ implementado / ❌ faltante / ⚠️ incompleto.
4. **Corregí** todos los ❌ y ⚠️ antes de continuar.
5. **Mostrá** el checklist completo con todos los ítems en ✅.
6. **Commit**: `git add -A && git commit -m "Fase N completa: [nombre] — checkpoint ✅"`
7. **Esperá** confirmación antes de avanzar.

---

## Orden de implementación — Rebanadas verticales

Cada fase entrega algo visible y funcional en el navegador.

### Fase 0 — Fundación
Scaffold del proyecto, Docker Compose, schema completo de DB, Alembic.
**Criterio**: `docker compose up` levanta todo. FastAPI conecta. Next.js responde. Todas las migraciones corren sin error.
> El schema va completo aquí porque modificarlo después es costoso.

### Fase 1 — Landing page y sistema de autenticación
Landing page de Whapi + registro bifurcado (dueño / empleado) + login + JWT + selector de comercios.
**Lo que se ve**: el usuario puede llegar a la landing, registrarse eligiendo su tipo, iniciar sesión y ver el selector de comercios.
**Spec UX**: landing page, flujo de registro, login, selector de comercios, mensaje si no tiene comercios.

### Fase 2 — Alta de comercio y gestión de empleados
Flujo de alta del primer comercio durante el registro del Dueño. ABM de comercios. Asociación de empleados a comercios con roles. Dar de baja a un empleado del comercio.
**Lo que se ve**: el Dueño crea su comercio, lo configura y asocia empleados con roles.
**Spec UX**: ajustes → empleados, ajustes → permisos. Spec: secciones 2.2, 2.7.

### Fase 3 — Sidebar de navegación y layout del panel
Sidebar colapsable con todos los ítems del menú. Tooltips en modo minimizado. Usuario autenticado en la esquina inferior izquierda con menú de editar perfil y logout. Switcher de comercio.
**Lo que se ve**: el panel completo con su navegación funcional, aunque las secciones internas estén vacías.
**Spec UX**: estructura del sidebar, comportamiento expandido/minimizado, menú de usuario.

### Fase 4 — Catálogo: productos y combos
ABM de productos (pizzas, empanadas, bebidas): crear, editar, activar/desactivar. ABM de combos. Gestión de precios y variantes.
**Lo que se ve**: ajustes → productos y ajustes → combos funcionando con datos reales.
**Spec**: secciones 3, 4, 9, wireframes 12.5, 12.6.

### Fase 5 — Tablero de pedidos
Tablero Kanban de pedidos en tiempo real. Filtros por estado, pago, repartidor. Detalle de pedido con timeline de estados. Acciones según rol. Avance de estados. Cancelaciones.
**Lo que se ve**: pedidos → tablero funcional donde el cajero/cocinero/repartidor puede gestionar pedidos.
**Spec**: secciones 6.1–6.4, 8.2, 8.3, wireframes 12.1–12.3.

### Fase 6 — Pedidos manuales (telefónicos)
Formulario de carga manual: búsqueda de cliente por teléfono, armado del pedido con el catálogo, tipo de entrega, método de pago. Unificación de perfil por teléfono.
**Lo que se ve**: pedidos manuales → formulario completo y funcional.
**Spec**: sección 8.4, wireframe 12.8.

### Fase 7 — Clientes y créditos
Listado de clientes del comercio. Detalle con historial de pedidos y saldo de crédito. Gestión manual de créditos por el Admin/Dueño.
**Lo que se ve**: clientes → listado y detalle con toda la información.
**Spec**: secciones 5.5, 6.4.

### Fase 8 — Conversaciones activas (HITL)
Lista de derivaciones en espera. Vista de chat + pedido en curso. Herramientas del operador. Devolver al bot / cerrar sin pedido.
**Lo que se ve**: panel de chats activos donde el cajero puede atender clientes derivados.
**Spec**: sección 5.8, wireframe 12.7.

### Fase 9 — Gestión de números de WhatsApp
Listado de números vinculados al comercio. Estado de sesión WPPConnect. Agregar número (QR). Desactivar / eliminar.
**Lo que se ve**: ajustes → teléfonos (o dentro de configuración del comercio).
**Spec**: sección 2.7 (múltiples WhatsApp), wireframe 12.10.

### Fase 10 — Webhooks, pagos y notificaciones
Endpoints de webhook para WPPConnect (routing de tenant por número destino) y MercadoPago. Notificaciones automáticas al cliente. Lógica de cancelaciones con crédito/reembolso. Incidencias y re-despacho.
**Lo que se ve**: pedidos se crean/actualizan automáticamente desde WhatsApp y pagos.
**Spec**: secciones 5.7, 6.4, 6.5, 7, 11.

### Fase 11 — Flujos de n8n
JSON importables: chatbot principal, notificaciones de estado, timer de inactividad. README con instrucciones.
**Lo que se ve**: flujos importados en n8n → chatbot de WhatsApp responde a clientes reales.
**Spec**: secciones 5.1–5.6.

### Fase 12 — Reportes
Reportes por comercio: ventas, cancelaciones, incidencias, métodos de pago. Filtros de fecha. Reporte consolidado del Dueño.
**Lo que se ve**: reportes → dashboards con métricas reales del comercio.
**Spec**: sección 10, wireframe 12.4.
