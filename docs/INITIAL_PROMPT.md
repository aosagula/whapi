# INITIAL_PROMPT — Whapi: Plataforma SaaS de Chatbot de Pedidos para Comercios

## Contexto del proyecto

Vas a construir **Whapi**, una plataforma SaaS multi-tenant que permite a dueños de comercios gastronómicos gestionar pedidos recibidos por WhatsApp, con panel web para su equipo y chatbot conversacional con LLM.

Leé estos dos archivos completos antes de hacer cualquier cosa:
- `CLAUDE.md` — stack, convenciones, modelo de navegación, UX y orden de fases
- `docs/especificacion-chatbot-pizzeria-v1.8.md` — especificación funcional del sistema (v1.8)
- prototipo en el archivo `docs/whapi-opcion-b-v2.html`
---

## Qué es Whapi

- Una **landing page pública** que muestra las características del producto para el dueño de un comercio.
- Un **panel web** para que el equipo del comercio gestione pedidos en tiempo real.
- Un **chatbot de WhatsApp** que toma pedidos con un LLM como motor conversacional.
- Arquitectura **multi-tenant**: cada comercio es un tenant aislado.

---

## Infraestructura ya existente — NO tocar

| Servicio          | Estado       | Qué hacer                                                          |
|-------------------|--------------|--------------------------------------------------------------------|
| WPPConnect Server | ✅ Corriendo | Consumir su API. Gestiona múltiples sesiones WhatsApp.             |
| PostgreSQL        | ✅ Corriendo | Instancia vacía. Alembic crea todo el schema.                      |
| n8n               | ✅ Instalado | Sin flujos. Se entregan en Fase 11 como JSON importables.          |

---

## Modelo de usuarios (leer con atención)

### Registro bifurcado
El registro distingue dos tipos de usuario:

**Dueño de comercio**
1. Completa sus datos de cuenta
2. Obligatoriamente da de alta su primer comercio (nombre, dirección, logo)
3. Opcionalmente conecta un número de WhatsApp (puede hacerlo después)
4. Queda automáticamente asociado al comercio con rol `dueño`

**Empleado / colaborador**
1. Solo completa sus datos de cuenta
2. No crea comercio. Accede cuando un Dueño lo asocie a un comercio con un rol.

### Post-login
Después de autenticarse, el sistema muestra los comercios a los que el usuario está asociado.
Si no tiene ninguno → mensaje informativo, sin acceso al panel.
Si tiene uno → entra directamente.
Si tiene más de uno → selector para elegir con cuál operar.

---

## Navegación del panel (implementar exactamente así)

### Sidebar izquierdo colapsable
- **Expandido**: icono + nombre de cada ítem
- **Minimizado**: solo iconos; hover → tooltip con el nombre

**Estructura del menú:**
```
📦  Pedidos
📞  Pedidos manuales
👥  Clientes
⚙️  Ajustes
    ├── 🔐  Permisos
    ├── 👤  Empleados
    ├── 🍕  Productos
    └── 🎁  Combos
📊  Reportes
    └── [reportes del comercio activo]
```

**Usuario autenticado — esquina inferior izquierda del sidebar:**
- Expandido: avatar + nombre completo
- Minimizado: solo avatar
- Al hacer clic → menú con: "Editar perfil" y "Cerrar sesión"

---

## Tu primera tarea — Fase 0: Fundación

### Antes de escribir código, presentá:

1. **Árbol de directorios** completo del proyecto (`whapi/`)
2. **docker-compose.yml** — solo `backend` y `frontend`
3. **Schema completo de la base de datos**: todas las tablas, columnas, tipos, FKs y constraints. El schema va completo en la Fase 0 porque modificarlo después de tener migraciones es costoso.
4. **Lista de archivos** que vas a crear
5. **Preguntas** si algo es ambiguo

### Criterio de éxito — Fase 0

- `docker compose up` sin errores
- `GET http://localhost:8000/health` → `{"status": "ok"}`
- `GET http://localhost:3000` → landing page de Whapi visible
- FastAPI conecta a PostgreSQL sin error
- Todas las migraciones Alembic corren sin error
- `.env.example` con todas las variables documentadas

### Checkpoint de la Fase 0

Antes del commit, verificá que el schema cubre:
- [ ] Tablas de cuenta: `usuario`, `comercio`, `usuario_comercio` (asociación con rol)
- [ ] Tablas de catálogo: `producto`, `catalogo_item`, `combo`, `combo_item`
- [ ] Tablas operativas: `cliente`, `pedido`, `item_pedido`, `pago`, `incidencia`, `sesion_conversacion`, `credito`
- [ ] Tabla de WhatsApp: `telefono_whatsapp` (sesión WPPConnect por número)
- [ ] Todas las tablas operativas tienen `comercio_id` como FK no nula
- [ ] Soft delete donde corresponde (`disponible`, `activo`, `eliminado_en`)
- [ ] Timestamps en UTC en todas las tablas
- [ ] El schema cubre los estados de pedido de la spec (sección 6)

---

## Protocolo de Checkpoint — aplicar al final de CADA fase

1. Releé las secciones de la spec y de `CLAUDE.md` que corresponden a la fase
2. Generá el checklist con funcionalidades, reglas de negocio, comportamientos de UI y casos borde
3. Verificá el código: ✅ implementado / ❌ faltante / ⚠️ incompleto
4. Corregí todos los ❌ y ⚠️
5. Mostrá el checklist con todos en ✅
6. `git add -A && git commit -m "Fase N completa: [nombre] — checkpoint ✅"`
7. Esperá mi confirmación antes de avanzar

---

## Secuencia de fases

| Fase | Qué construye                              | Lo que se ve en el navegador                        |
|------|--------------------------------------------|-----------------------------------------------------|
| 0    | Scaffold + schema completo de DB           | Landing page básica, FastAPI conecta a DB           |
| 1    | Landing + auth + registro + selector       | Registro bifurcado, login, selector de comercios    |
| 2    | Alta de comercio + empleados + roles       | El Dueño crea su comercio y agrega empleados        |
| 3    | Sidebar colapsable + layout del panel      | Navegación completa con todos los ítems del menú    |
| 4    | Catálogo: productos y combos               | ABM de menú completo desde ajustes                  |
| 5    | Tablero de pedidos (Kanban)                | Gestión de pedidos por estados según rol            |
| 6    | Pedidos manuales (telefónicos)             | Formulario de carga de pedido por teléfono          |
| 7    | Clientes y créditos                        | Listado de clientes con historial y saldo           |
| 8    | Conversaciones activas (HITL)              | El cajero atiende derivaciones de WhatsApp          |
| 9    | Gestión de números de WhatsApp             | El Dueño vincula números WhatsApp al comercio       |
| 10   | Webhooks + pagos + notificaciones          | Pedidos llegan automáticamente desde WhatsApp       |
| 11   | Flujos de n8n                              | El chatbot responde clientes en WhatsApp            |
| 12   | Reportes                                   | Métricas y reportes por comercio                    |

---

## Comienza ahora

Leé `docs/especificacion-chatbot-pizzeria.md` y `CLAUDE.md` completamente.
Presentá el plan para la Fase 0 (árbol de directorios + schema de DB + lista de archivos).
**No escribas código hasta que yo apruebe el plan.**
