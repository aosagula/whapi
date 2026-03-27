# INITIAL_PROMPT — Plataforma de Chatbot de Pedidos para Pizzerías (Multi-Tenant)

## Contexto del proyecto

Vas a construir una **plataforma SaaS multi-tenant** de gestión de pedidos para pizzerías.
La especificación funcional completa está en `docs/especificacion-chatbot-pizzeria.md` (v1.8). **Leé ese archivo completo antes de hacer cualquier cosa.** Prestá especial atención a la sección 2.7 (Multi-tenancy, registro y múltiples WhatsApp).

El archivo `CLAUDE.md` define el stack, las convenciones y el orden de implementación. Seguilo estrictamente.

---

## Concepto clave — Multi-tenancy

El sistema atiende a múltiples pizzerías desde una misma plataforma. Un **Dueño** se registra, crea una o más pizzerías, y cada pizzería tiene su propio menú, empleados, clientes y números de WhatsApp. Los datos están completamente aislados entre pizzerías.

```
Cuenta (Dueño)
  └── Pizzería A
  │     ├── Números de WhatsApp (sesiones WPPConnect)
  │     ├── Empleados (cajero, cocinero, repartidor, admin)
  │     ├── Menú y catálogo propio
  │     └── Pedidos y clientes propios
  └── Pizzería B
        └── ...
```

**Regla de oro**: todo query operativo filtra siempre por `pizzeria_id`. Sin excepciones.

---

## Infraestructura ya existente — NO tocar

| Servicio              | Estado                                                        |
|-----------------------|---------------------------------------------------------------|
| **WPPConnect Server** | ✅ Corriendo. Gestiona múltiples sesiones (una por número de WhatsApp). Recibe y envía mensajes. |
| **PostgreSQL**        | ✅ Instancia corriendo, sin schema. Alembic creará todo.      |
| **n8n**               | ✅ Instalado, sin flujos. Los flujos se entregan como JSON importables (Fase 15). |

---

## Lo que hay que construir

1. **Backend (FastAPI)** — API REST multi-tenant + webhooks para WPPConnect y MercadoPago
2. **Frontend (Next.js)** — Panel web con registro, selector de pizzería y panel operativo
3. **Flujos de n8n** — JSON importables (chatbot, notificaciones, timer de inactividad)
4. **Schema de base de datos** — Vía migraciones Alembic

---

## Tu primera tarea — Fase 0: Scaffold del proyecto

**Antes de escribir código, presentá el siguiente plan:**

1. **Árbol de directorios** completo del proyecto
2. **docker-compose.yml** — solo `backend` y `frontend` (PostgreSQL, WPPConnect y n8n ya corren en el entorno)
3. **Lista de archivos** que vas a crear en la Fase 0
4. **Preguntas** si algo de la spec es ambiguo antes de arrancar

### Criterio de éxito para la Fase 0

- `docker compose up` levanta backend y frontend sin errores
- `GET http://localhost:8000/health` → `{"status": "ok"}`
- `GET http://localhost:3000` → página de login/registro vacía pero funcional
- FastAPI conecta a PostgreSQL sin error (verificar en el startup log)
- `.env.example` documenta todas las variables necesarias

### Al terminar la Fase 0

1. `git add -A && git commit -m "Fase 0: scaffold inicial del proyecto"`
2. Mostrá el resumen de lo creado
3. **Esperá mi confirmación** antes de avanzar a la Fase 1 (schema de DB)

---

## Reglas de trabajo

- **Planificá antes de implementar**: mostrá el plan, esperá aprobación, ejecutá
- **Commit antes de cambios grandes**: schema, refactors, inicio de módulo nuevo
- **Un módulo a la vez**
- **Consultá la spec ante cualquier duda de negocio**
- **Nunca hardcodear valores**: todo por `.env`

---

## Referencia rápida — Entidades del dominio

### Nivel de cuenta (cross-tenant)
| Entidad         | Descripción                                                    |
|-----------------|----------------------------------------------------------------|
| `Cuenta`        | Datos del Dueño: email, contraseña, nombre, teléfono          |
| `Pizzeria`      | Tenant principal. Nombre, dirección, logo. Pertenece a Cuenta. |
| `UsuarioCuenta` | Empleado del panel. Puede tener roles en múltiples pizzerías.  |
| `RolPizzeria`   | Asignación de rol de un usuario a una pizzería específica.     |

### Nivel de pizzería (siempre filtrar por `pizzeria_id`)
| Entidad              | Descripción                                                  |
|----------------------|--------------------------------------------------------------|
| `NumeroWhatsApp`     | Sesión WPPConnect de esa pizzería. Estado: conectado / desconectado. |
| `Producto`           | Inventario base: Pizza / Empanada / Bebida                   |
| `CatalogoItem`       | Precio y variantes de cada producto en esa pizzería          |
| `Combo`              | Agrupa productos con precio especial                         |
| `Cliente`            | Identificado por teléfono, scoped a la pizzería              |
| `Credito`            | Saldo a favor del cliente en esa pizzería                    |
| `Pedido`             | Origen: `whatsapp` / `telefonico` / `operador`               |
| `ItemPedido`         | Líneas del pedido                                            |
| `Pago`               | Estado de pago independiente                                 |
| `Incidencia`         | Problema durante o después del delivery                      |
| `SesionConversacion` | Estado del chat WhatsApp (incluye `numero_whatsapp_id`)      |

### Roles
`dueno` (nivel cuenta) › `admin` › `cajero` › `cocinero` › `repartidor` (todos nivel pizzería)

### Estados de pedido
```
pedido_en_curso → pendiente_pago → pendiente_preparacion
    → en_preparacion → a_despacho → en_delivery → entregado
Desvíos: cancelado | con_incidencia | descartado
```

---

## Comienza ahora

Leé `docs/especificacion-chatbot-pizzeria.md` (v1.8) y `CLAUDE.md` completamente.
Luego presentá el plan detallado para la Fase 0. No escribas código hasta que yo apruebe el plan.
