# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Regla de oro

Antes de escribir cualquier código, presentá el plan de implementación del paso actual y esperá confirmación.

## Spec y documentación

La especificación funcional completa está en `docs/especificacion-chatbot-pizzeria.md`. Ante cualquier duda de comportamiento o regla de negocio, consultarla primero. El archivo `docs/CLAUDE.md` contiene UX, navegación y el orden de fases de implementación.

## Comandos de desarrollo

### Backend (FastAPI)
```bash
# Levantar todo
docker compose up

# Solo backend en desarrollo
cd backend && uvicorn app.main:app --reload --port 8000

# Migraciones
cd backend && alembic upgrade head
cd backend && alembic revision --autogenerate -m "descripcion"

# Tests
cd backend && pytest
cd backend && pytest tests/test_pedidos.py::test_crear_pedido  # test individual

# Tests frontend (Testing Library + Jest/Vitest)
cd frontend && npm run test
cd frontend && npm run test -- components/kanban/KanbanBoard.test.tsx  # test individual

# Tests E2E con Playwright
cd frontend && npx playwright test
cd frontend && npx playwright test e2e/pedidos.spec.ts  # test individual
cd frontend && npx playwright test --ui                 # modo visual

# Linting
cd backend && ruff check app/
cd backend && mypy app/
```

### Frontend (Next.js)
```bash
cd frontend && npm run dev    # http://localhost:3000
cd frontend && npm run build
cd frontend && npm run lint
```

## Arquitectura

### Stack
| Componente | Tecnología |
|---|---|
| API | FastAPI (Python 3.12+) |
| DB | PostgreSQL 16 + SQLAlchemy 2.x + Alembic |
| Frontend | Next.js 14 App Router + TypeScript + shadcn/ui + Tailwind |
| WhatsApp | WPPConnect Server (ya corriendo — solo consumir) |
| Automatización | n8n (ya instalado — flujos en `n8n-flows/` como JSON importables) |
| Infra | Docker Compose solo para `backend` y `frontend` |

### Multi-tenancy

**Todo query operativo filtra siempre por `comercio_id`. Sin excepciones.**

```
Cuenta (Usuario)
  └── Comercio A  ←── tenant
        ├── TelefonoWhatsApp (1..N sesiones WPPConnect)
        ├── Empleados (con roles: dueño | admin | cajero | cocinero | repartidor)
        ├── Catálogo propio
        └── Pedidos y clientes propios (cliente scoped: mismo tel = distinto cliente por comercio)
```

### Estructura del proyecto
```
backend/app/
  api/          # Un router por dominio (auth, pedidos, clientes, catalogo, webhooks…)
  models/       # SQLAlchemy models (todos con comercio_id FK no nula, salvo usuario/cuenta)
  schemas/      # Pydantic schemas
  core/         # config.py, db.py, auth.py (JWT), deps.py, tenant.py (middleware)
  services/     # Lógica de negocio (no en los routers)
frontend/app/
  (auth)/       # login, register — layout sin sidebar
  selector/     # Selector de comercio post-login
  [pizzeria_id]/ # Panel operativo con sidebar: dashboard, pedidos, conversaciones, menu, reportes, configuracion
frontend/components/
  kanban/       # Tablero de pedidos
  conversaciones/  # Vista HITL
  pedido-telefonico/  # Formulario de carga manual
n8n-flows/      # JSON importables: chatbot, notificaciones, timer de inactividad
```

### Flujo de autenticación
1. Login → JWT → `/selector` (si tiene >1 comercio) o directo al panel
2. Sin comercios asociados → mensaje informativo, sin acceso al panel
3. Todos los endpoints del panel requieren `comercio_id` del contexto autenticado

### Webhook routing (WPPConnect)
El webhook entrante identifica el tenant por el número WhatsApp destino (`TelefonoWhatsApp`). Un comercio puede tener múltiples números, cada uno con su propia sesión WPPConnect.

### HITL (Human-in-the-Loop)
Conversaciones en estado `derivada_humano` suspenden el LLM. El cajero las atiende desde el panel de conversaciones y puede devolver al bot o cerrar sin pedido.

## Convenciones de código

### Python
- `from __future__ import annotations` en todos los módulos
- **Comentarios y docstrings en español; nombres de modelos, atributos y variables en inglés**
- Endpoints operativos reciben `comercio_id` del contexto autenticado (nunca del body)
- Nunca eliminar productos físicamente si tienen pedidos históricos — usar `disponible = false`

### TypeScript
- Strict mode; nunca `any`
- Server Components por defecto; Client Components solo cuando sea necesario
- Componentes en PascalCase
- **Comentarios en español; nombres de variables, props, tipos e interfaces en inglés**

### Base de datos
- Migraciones siempre con Alembic, nunca DDL manual
- Soft delete: `disponible` (productos), `activo` (otros), `eliminado_en` (timestamp)
- Timestamps en UTC

## Variables de entorno (`.env`)
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

## Reglas de negocio críticas

1. Todo query operativo filtra por `comercio_id`
2. Mismo teléfono = clientes distintos en distintos comercios
3. Al crear un comercio, el Dueño queda asociado automáticamente con rol `dueño`
4. Código de producto: inmutable y único dentro del comercio
5. Mitad y mitad: precio = mayor de los dos gustos + recargo configurable por comercio
6. Cancelaciones: nunca eliminar, solo cambiar estado; crédito se restituye según spec sección 6.4
7. Origen del pedido siempre registrado: `whatsapp` / `telefonico` / `operador`
8. LLM suspendido cuando conversación está en `derivada_humano`

## Workflow de implementación

1. **Planificá primero**: mostrá qué vas a hacer y esperá confirmación
2. **Commit antes de cambios grandes**: schema, refactors, inicio de módulo nuevo
3. **Un módulo a la vez**: no avanzar al siguiente hasta que el actual esté funcionando
4. **Tests por fase**: cada fase incluye tests de backend (`pytest`), tests de componentes (Testing Library) y tests de navegación E2E (Playwright MCP); todos deben pasar antes del checkpoint
5. **Checkpoint al final de cada fase**: ver protocolo en `docs/CLAUDE.md`
6. **Git**: mensajes en español, en infinitivo

## Tests E2E con Playwright MCP

### Integración del MCP

El MCP de Playwright permite que Claude controle el browser directamente para ejecutar y validar tests de navegación.

**1. Instalar el servidor MCP** (una sola vez, global):
```bash
npm install -g @playwright/mcp
```

**2. Registrar en Claude Code** — agregar en `~/.claude/settings.json` (o via `/mcp`):
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp"]
    }
  }
}
```

**3. Instalar Playwright en el proyecto frontend**:
```bash
cd frontend && npm install -D @playwright/test
npx playwright install chromium
```

**4. Configuración** — `frontend/playwright.config.ts`:
```ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  use: {
    baseURL: 'http://localhost:3000',
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
  },
})
```

### Estructura de tests E2E
```
frontend/e2e/
  auth.spec.ts          # login, registro, selector de comercio
  pedidos.spec.ts       # tablero kanban, cambio de estados
  pedido-telefonico.spec.ts
  catalogo.spec.ts      # ABM productos y combos
  conversaciones.spec.ts
```

### Cobertura mínima por fase
Cada spec cubre: navegación a la ruta, render de elementos clave, flujo principal (ej: crear un pedido, cambiar estado), y manejo de error visible al usuario.

## Git
```bash
git add -A && git commit -m "Agregar endpoint de cancelación de pedidos"
```
