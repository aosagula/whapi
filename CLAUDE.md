# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workflow rules (mandatory)

1. **Plan before implementing**: Present the implementation plan for the current phase and wait for confirmation before writing any code.
2. **Commit before large changes**: Before refactoring, changing project structure, or modifying the DB schema, commit current work first with `git add -A && git commit -m "..."`.
3. **One module at a time**: Do not advance to the next module until the current one is working and tested.
4. **Consult the spec on business ambiguity**: The full functional spec is at `docs/especificacion-chatbot-pizzeria-v1.8.md`. Always reference it.

Git commit messages: in Spanish, in infinitive form (e.g., "Agregar endpoint de pedidos").

## Project overview

Multi-tenant SaaS platform for pizza shop ordering management via WhatsApp chatbot. A **Dueño** (account owner) registers, creates one or more pizzerias, and each pizzeria has its own menu, employees, clients, and WhatsApp numbers. Data is completely isolated between pizzerias.

## Tech stack

| Component | Technology |
|-----------|-----------|
| Backend API | FastAPI (Python 3.12+) |
| Database | PostgreSQL 16 + SQLAlchemy 2.x + Alembic |
| Frontend | Next.js 14 (App Router) + TypeScript |
| UI | shadcn/ui + Tailwind CSS |
| WhatsApp | WPPConnect Server (already running — consume only) |
| Automation | n8n (already installed — deliver flows as importable JSON) |
| Infrastructure | Docker Compose for backend + frontend only |

## Existing infrastructure — DO NOT recreate

| Service | Status | Action |
|---------|--------|--------|
| WPPConnect Server | Running | Consume its API / receive webhooks. Manages multiple sessions (one per WhatsApp number). |
| PostgreSQL | Running (no schema) | Create schema via Alembic only |
| n8n | Installed (no flows) | Create flows as part of this project (Phase 15) |

## Multi-tenant architecture (critical)

**Every pizzeria is an isolated tenant.** No endpoint may return data from another pizzeria. This is enforced at middleware and query level.

```
Cuenta (Dueño)
  └── Pizzería 1
  │     ├── NumeroWhatsApp (1..N WPPConnect sessions)
  │     ├── Empleados (roles: admin / cajero / cocinero / repartidor)
  │     ├── Catálogo (productos, combos, precios)
  │     ├── Clientes (scoped — same phone can exist in two pizzerias)
  │     └── Pedidos
  └── Pizzería 2
```

- Every authenticated employee request carries an active `pizzeria_id` in the JWT or header.
- All queries to operational tables (`pedidos`, `clientes`, `productos`, `sesiones`, etc.) **always filter by `pizzeria_id`** — no exceptions.
- The `dueno` role can switch active pizzeria from the panel; other roles are fixed to their pizzeria.

## Project structure (planned)

```
pizzeria-chatbot/
├── docker-compose.yml         # Backend + frontend only
├── .env.example
├── docs/
├── backend/                   # FastAPI
│   ├── app/
│   │   ├── api/               # auth, webhooks, pedidos, clientes, catalogo, pizzerias, whatsapp, empleados, reportes
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   ├── core/              # config, db, auth (JWT + tenant context), tenant (isolation middleware)
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   └── Dockerfile
├── frontend/                  # Next.js
│   ├── app/
│   │   ├── (auth)/            # Login, registration
│   │   ├── selector/          # Pizzeria selector (post-login)
│   │   └── [pizzeria]/        # Operational panel (pizzeria-scoped)
│   ├── components/
│   ├── lib/
│   └── Dockerfile
└── n8n-flows/
    ├── chatbot-principal.json
    ├── notificaciones.json
    └── inactividad-timer.json
```

## Domain entities

**Account level (cross-tenant):** `Cuenta`, `Pizzeria`, `UsuarioCuenta`, `RolPizzeria`

**Pizzeria level (always filter by `pizzeria_id`):** `NumeroWhatsApp`, `Producto`, `CatalogoItem`, `Combo`, `Cliente`, `Credito`, `Pedido`, `ItemPedido`, `Pago`, `Incidencia`, `SesionConversacion`

**Roles:** `dueno` (account-level, cross-pizzeria visibility) › `admin` › `cajero` › `cocinero` › `repartidor` (all pizzeria-level)

**Order states:**
```
pedido_en_curso → pendiente_pago → pendiente_preparacion
    → en_preparacion → a_despacho → en_delivery → entregado
Desvíos: cancelado | con_incidencia | descartado
```

## Code conventions

**Python (FastAPI):**
- Strict typing: `from __future__ import annotations`
- All values via environment variables — never hardcode
- snake_case file names; one router per domain
- All operational endpoints receive `pizzeria_id` from authenticated context
- Docstrings in Spanish

**TypeScript (Next.js):**
- Strict mode enabled; never use `any`
- PascalCase components; Server Components by default

**Database:**
- Migrations always via Alembic
- All operational tables have `pizzeria_id` as non-null FK
- Soft delete for products and orders (never physically delete if historical orders exist)
- Timestamps in UTC; product codes are immutable and unique within a pizzeria

## Environment variables

```
DATABASE_URL=postgresql://user:pass@host:5432/pizzeria
SECRET_KEY=
ACCESS_TOKEN_EXPIRE_MINUTES=60
WPPCONNECT_BASE_URL=
WPPCONNECT_SECRET_KEY=
N8N_WEBHOOK_BASE_URL=
MERCADOPAGO_ACCESS_TOKEN=
OPENAI_API_KEY=   # or ANTHROPIC_API_KEY=
```

## Critical business rules

1. Tenant isolation: every operational query filters by `pizzeria_id`. No exceptions.
2. Same phone number = different clients in different pizzerias.
3. WPPConnect multi-session: each `NumeroWhatsApp` has its own session. Incoming webhooks identify the pizzeria by the destination number.
4. Credits (`Credito`) are tied to the client in that specific pizzeria — not transferable.
5. Half-and-half pizza price = higher of the two flavors + configurable surcharge per pizzeria.
6. Cancellations: never delete, only change state (see spec section 6.4).
7. Products: never physically delete if they have historical orders — only set `disponible = false`.
8. HITL: the LLM is suspended when conversation is in `derivada_humano` state.
9. Order origin must always be recorded: `whatsapp` / `telefonico` / `operador`.

## Implementation phases

0. Scaffold + Docker Compose (backend + frontend)
1. Full DB schema + Alembic migrations (includes multi-tenancy)
2. Auth — account registration, login, JWT with pizzeria context, pizzeria selector
3. Pizzeria ABM + WhatsApp number management (Dueño)
4. Employee management + roles per pizzeria
5. Catalog ABM (inventory, pizzas, empanadas, drinks, combos)
6. Client management (CRUD + credits, scoped to pizzeria)
7. Order management (states, transitions, cancellations)
8. Webhooks (WPPConnect → FastAPI with tenant routing, MercadoPago)
9–14. Frontend panels (registration, Kanban board, menu, HITL, phone orders, WhatsApp/employee management)
15. n8n flows (importable JSON)
16. Reports (per-pizzeria + consolidated Dueño view)
