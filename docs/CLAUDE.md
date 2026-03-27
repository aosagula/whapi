# CLAUDE.md — Reglas del Proyecto: Chatbot Pizzería (Plataforma Multi-Tenant)

## Regla de oro
Antes de escribir cualquier código, presentá el plan de implementación del paso actual y esperá confirmación.

---

## Flujo de trabajo obligatorio

1. **Planificá primero**: Antes de implementar cualquier módulo, mostrá qué vas a hacer y cómo.
2. **Commit antes de cambios grandes**: Si vas a refactorizar, cambiar la estructura del proyecto o modificar el schema de la DB, hacé `git add -A && git commit -m "..."` con los cambios actuales primero.
3. **Un módulo a la vez**: No avances al siguiente módulo hasta que el actual esté funcionando y testeado.
4. **Preguntá si algo es ambiguo**: Hay una especificación funcional detallada en `docs/especificacion-chatbot-pizzeria.md` — consultala siempre.

---

## Stack tecnológico

| Componente        | Tecnología                                      |
|-------------------|-------------------------------------------------|
| API principal     | FastAPI (Python 3.12+)                          |
| Base de datos     | PostgreSQL 16 (instancia ya existente, sin schema) |
| ORM               | SQLAlchemy 2.x + Alembic (migraciones)          |
| Panel web         | Next.js 14 (App Router) + TypeScript            |
| UI components     | shadcn/ui + Tailwind CSS                        |
| Bridge WhatsApp   | WPPConnect Server (ya corriendo, solo consumir) |
| Orquestador       | n8n (instalado, los flujos se crean en este proyecto) |
| Infraestructura   | Docker Compose solo para backend y frontend     |

---

## Infraestructura existente — NO recrear

| Servicio          | Estado                        | Qué hacer                              |
|-------------------|-------------------------------|----------------------------------------|
| WPPConnect Server | ✅ Corriendo                  | Consumir su API / recibir webhooks. Gestiona múltiples sesiones simultáneas (una por número de WhatsApp). |
| PostgreSQL        | ✅ Instancia corriendo        | Crear el schema vía Alembic, nada más  |
| n8n               | ✅ Instalado                  | Crear los flujos como parte del proyecto |

---

## ⚠️ Arquitectura Multi-Tenant — Regla fundamental

**El sistema es una plataforma SaaS multi-tenant.** Cada pizzería es un tenant aislado.
Todo dato operativo (pedidos, clientes, menú, empleados) pertenece a una pizzería específica.
**Ningún endpoint puede devolver datos de otra pizzería.** Esto se garantiza a nivel de middleware y queries.

### Jerarquía de entidades

```
Cuenta (Dueño)
  └── Pizzería 1
  │     ├── NumeroWhatsApp (1..N sesiones WPPConnect)
  │     ├── Empleados (con roles: admin / cajero / cocinero / repartidor)
  │     ├── Catálogo (productos, combos, precios)
  │     ├── Clientes (por pizzería — mismo teléfono puede existir en dos pizzerías)
  │     └── Pedidos
  └── Pizzería 2
        └── ...
```

### Reglas de aislamiento

- Cada request autenticado de empleado incluye un `pizzeria_id` activo en el JWT o en el header.
- Todo query a tablas operativas (`pedidos`, `clientes`, `productos`, `sesiones`, etc.) **filtra siempre por `pizzeria_id`**.
- El rol `dueño` puede cambiar de pizzería activa desde el panel; los demás roles están fijos a su pizzería.
- Los clientes **no se comparten entre pizzerías**, aunque tengan el mismo número de teléfono.

---

## Estructura del proyecto

```
pizzeria-chatbot/
├── docker-compose.yml         # Solo backend + frontend
├── .env.example
├── docs/
│   └── especificacion-chatbot-pizzeria.md
├── backend/                   # FastAPI
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py        # Login, registro de cuenta, selector de pizzería
│   │   │   ├── webhooks.py    # Recibe eventos de WPPConnect y MercadoPago
│   │   │   ├── pedidos.py
│   │   │   ├── clientes.py
│   │   │   ├── catalogo.py
│   │   │   ├── pizzerias.py   # ABM de pizzerías (Dueño)
│   │   │   ├── whatsapp.py    # Gestión de números/sesiones WPPConnect
│   │   │   ├── empleados.py
│   │   │   └── reportes.py
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Lógica de negocio
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── db.py
│   │   │   ├── auth.py        # JWT + extracción de tenant context
│   │   │   └── tenant.py      # Middleware de aislamiento de tenant
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   └── Dockerfile
├── frontend/                  # Next.js
│   ├── app/
│   │   ├── (auth)/            # Login, registro
│   │   ├── selector/          # Selector de pizzería (post-login)
│   │   └── [pizzeria]/        # Panel operativo (scope de pizzería)
│   ├── components/
│   ├── lib/
│   └── Dockerfile
└── n8n-flows/
    ├── README.md
    ├── chatbot-principal.json
    ├── notificaciones.json
    └── inactividad-timer.json
```

---

## Entidades del dominio

### Nivel de cuenta (cross-tenant)
- `Cuenta` — datos del Dueño, email, contraseña
- `Pizzeria` — pertenece a una Cuenta; es el tenant
- `UsuarioCuenta` — el Dueño y sus empleados; un empleado puede tener roles en múltiples pizzerías

### Nivel de pizzería (scoped por `pizzeria_id`)
- `NumeroWhatsApp` — sesión WPPConnect vinculada a una pizzería
- `Producto` — inventario base de esa pizzería
- `CatalogoItem` — precios y variantes de cada producto
- `Combo` — agrupación de productos con precio especial
- `Cliente` — identificado por teléfono, scoped a la pizzería
- `Pedido` — con origen: `whatsapp` / `telefonico` / `operador`
- `ItemPedido`
- `Pago`
- `Incidencia`
- `SesionConversacion` — estado del chat WhatsApp (incluye `numero_whatsapp_id`)
- `Credito` — saldo a favor del cliente en esa pizzería

### Roles
- `dueno` — nivel de cuenta, visibilidad sobre todas sus pizzerías
- `admin` — nivel de pizzería, acceso completo operativo
- `cajero` — nivel de pizzería
- `cocinero` — nivel de pizzería
- `repartidor` — nivel de pizzería

---

## Convenciones de código

### Python (FastAPI)
- Tipado estricto: `from __future__ import annotations`
- Nunca hardcodear valores: todo por variables de entorno
- Nombres de archivos en snake_case
- Un router por dominio
- Todos los endpoints operativos reciben el `pizzeria_id` del contexto autenticado
- Docstrings en español

### TypeScript (Next.js)
- Strict mode activado
- Componentes en PascalCase
- Server Components por defecto
- Nunca usar `any`

### Base de datos
- Migraciones siempre con Alembic
- Todas las tablas operativas tienen `pizzeria_id` como FK no nula
- Soft delete para productos y pedidos
- Timestamps en UTC

---

## Variables de entorno

```
# Base de datos
DATABASE_URL=postgresql://user:pass@host:5432/pizzeria

# Auth
SECRET_KEY=
ACCESS_TOKEN_EXPIRE_MINUTES=60

# WPPConnect (gestiona múltiples sesiones)
WPPCONNECT_BASE_URL=
WPPCONNECT_SECRET_KEY=

# n8n
N8N_WEBHOOK_BASE_URL=

# MercadoPago
MERCADOPAGO_ACCESS_TOKEN=

# LLM
OPENAI_API_KEY=
# o ANTHROPIC_API_KEY=
```

---

## Git

- Mensajes en español, en infinitivo
- Commit obligatorio antes de: cambios de schema, refactors, inicio de nuevo módulo
- Nunca commitear `.env`, `__pycache__`, `node_modules`, `.next`

---

## Reglas de negocio críticas

1. **Aislamiento de tenant**: Todo query operativo filtra por `pizzeria_id`. Sin excepciones.
2. **Cliente scoped a pizzería**: El mismo número de teléfono puede ser dos clientes distintos en dos pizzerías.
3. **WPPConnect multi-sesión**: Cada `NumeroWhatsApp` tiene su propia sesión. El webhook entrante identifica a qué pizzería pertenece por el número destino.
4. **Crédito**: Asociado al cliente en esa pizzería. No es transferible entre pizzerías.
5. **Mitad y mitad**: Precio = el mayor de los dos gustos + recargo configurable por pizzería.
6. **Cancelaciones**: Ver spec sección 6.4. No eliminar, solo cambiar estado.
7. **Productos**: Nunca eliminar físicamente si tienen pedidos históricos. Solo `disponible = false`.
8. **Código de producto**: Inmutable. Único dentro de la pizzería.
9. **Roles**: Respetar permisos de la spec (secciones 2, 8). El Dueño tiene visibilidad cross-pizzería.
10. **HITL**: El LLM se suspende en estado `derivada_humano`.
11. **Origen del pedido**: Siempre registrar: `whatsapp` / `telefonico` / `operador`.

---

## Orden de implementación

1. **Fase 0**: Scaffold + Docker Compose (backend + frontend)
2. **Fase 1**: Schema completo de base de datos + migraciones Alembic (incluye multi-tenancy)
3. **Fase 2**: Auth — registro de cuenta, login, JWT con contexto de pizzería, selector de pizzería
4. **Fase 3**: ABM de pizzerías y gestión de números de WhatsApp (Dueño)
5. **Fase 4**: Gestión de empleados + roles por pizzería
6. **Fase 5**: ABM de catálogo (inventario, pizzas, empanadas, bebidas, combos)
7. **Fase 6**: Gestión de clientes (CRUD + créditos, scoped a pizzería)
8. **Fase 7**: Gestión de pedidos (estados, transiciones, cancelaciones)
9. **Fase 8**: Webhooks (WPPConnect → FastAPI con routing de tenant, MercadoPago)
10. **Fase 9**: Panel web — registro y selector de pizzería
11. **Fase 10**: Panel web — tablero Kanban de pedidos
12. **Fase 11**: Panel web — ABM de menú
13. **Fase 12**: Panel web — conversaciones activas (HITL)
14. **Fase 13**: Panel web — pedido telefónico manual
15. **Fase 14**: Panel web — gestión de WhatsApp y empleados
16. **Fase 15**: Flujos de n8n (JSON importables)
17. **Fase 16**: Reportes (por pizzería + consolidado del Dueño)
