# Especificación Funcional — Chatbot de Pedidos para Pizzería

**Versión:** 1.8
**Fecha:** Marzo 2026
**Estado:** Borrador

**Historial de cambios:**
| Versión | Fecha       | Descripción                                      |
|---------|-------------|--------------------------------------------------|
| 1.0     | Mar 2026    | Versión inicial                                  |
| 1.1     | Mar 2026    | Agrega código/ID y nombre corto a productos; nueva sección de Inventario / Lista de Productos |
| 1.2     | Mar 2026    | Reemplaza flujo de menú numerado por arquitectura conversacional basada en LLM; agrega gestión de datos del cliente y detección de cliente trabado |
| 1.3     | Mar 2026    | Agrega sección 5.6: cierre de sesión por inactividad de 10 minutos con consulta previa al cliente |
| 1.4     | Mar 2026    | Corrige inconsistencias; agrega estados Cancelado y Con Incidencia; política de cancelaciones; flujo de incidencias y re-despacho; notificaciones diferenciadas por tipo de entrega; reporte de cancelaciones e incidencias |
| 1.5     | Mar 2026    | El cliente puede consultar su crédito disponible vía WhatsApp en cualquier momento |
| 1.6     | Mar 2026    | Agrega sección 5.8: flujo completo de derivación a operador humano (HITL), estados de sesión, permisos y wireframe |
| 1.7     | Mar 2026    | Agrega sección 8.4: pedido telefónico manual desde el panel; unificación de perfil de cliente por teléfono; campo de origen del pedido (WhatsApp / Telefónico / Operador) |
| 1.8     | Mar 2026    | Arquitectura multi-tenant: rol de Dueño, registro de pizzería, múltiples pizzerías por cuenta, múltiples WhatsApp por pizzería, aislamiento de datos entre tenants |

---

## Índice

1. [Visión General](#1-visión-general)
2. [Actores y Roles](#2-actores-y-roles) — incluye Registro, Multi-tenancy y Múltiples WhatsApp (2.7)
3. [Inventario / Lista de Productos](#3-inventario--lista-de-productos)
4. [Catálogo de Productos](#4-catálogo-de-productos)
5. [Flujo del Chatbot (WhatsApp)](#5-flujo-del-chatbot-whatsapp)
6. [Estados de un Pedido](#6-estados-de-un-pedido) — incluye Política de Cancelaciones (6.4) y Gestión de Incidencias (6.5)
7. [Flujo de Pago](#7-flujo-de-pago)
8. [Aplicación Web — Panel de Gestión](#8-aplicación-web--panel-de-gestión)
9. [ABM de Menú, Precios e Inventario](#9-abm-de-menú-precios-e-inventario)
10. [Reportes](#10-reportes)
11. [Integraciones](#11-integraciones)
12. [Wireframes de Pantallas Principales](#12-wireframes-de-pantallas-principales)

---

## 1. Visión General

El sistema es una **plataforma multi-tenant**: un mismo sistema atiende a múltiples pizzerías, cada una con su propio menú, equipo, números de WhatsApp y datos de clientes, completamente aislados entre sí. Un Dueño puede registrar y gestionar varias pizzerías desde una única cuenta.

El sistema consiste en tres componentes integrados:

**Chatbot de WhatsApp**: Permite a los clientes de la pizzería realizar pedidos desde WhatsApp de forma conversacional, impulsado por un LLM. El bot guía al cliente en la selección de productos, arma el resumen del pedido, ofrece opciones de pago y mantiene al cliente informado del estado en tiempo real. Cada pizzería puede tener uno o más números de WhatsApp; todos se atienden desde el mismo panel.

**Motor de automatización (n8n)**: Orquesta todos los flujos: recepción de mensajes de WPPConnect, gestión del estado del pedido, envío de links de pago de MercadoPago, derivaciones a operadores humanos y notificaciones.

**Panel Web de Gestión**: Aplicación web donde el personal de cada pizzería visualiza y administra los pedidos en tiempo real, gestiona el menú y consulta reportes de ventas. El Dueño accede a un panel de cuenta con visibilidad sobre todas sus pizzerías.

---

## 2. Actores y Roles

El sistema es **multi-tenant**: cada pizzería es una cuenta independiente. Los roles se asignan siempre en el contexto de una pizzería específica, excepto el rol de Dueño, que opera a nivel de cuenta y puede gestionar múltiples pizzerías.

### Jerarquía de roles

```
DUEÑO / PROPIETARIO
    │  (puede tener varias pizzerías)
    │
    ├── PIZZERÍA A
    │       ├── Administrador
    │       ├── Cajero / Cobrador
    │       ├── Preparador / Cocinero
    │       └── Repartidor / Delivery
    │
    └── PIZZERÍA B
            ├── Administrador
            └── ...
```

### 2.1 Cliente (vía WhatsApp)
Persona que interactúa con el chatbot para realizar su pedido. No requiere registro previo; se identifica por su número de WhatsApp. Es siempre un cliente de una pizzería específica, no de la plataforma en general.

### 2.2 Dueño / Propietario
Es el usuario que registra su cuenta en la plataforma y da de alta una o más pizzerías.
- Accede a un **panel de cuenta** donde puede ver y cambiar entre todas sus pizzerías.
- Da de alta, edita y desactiva pizzerías.
- Gestiona los números de WhatsApp de cada pizzería.
- Agrega y elimina empleados (usuarios del panel) y les asigna roles por pizzería.
- Accede a los reportes de cada pizzería y a un resumen consolidado multi-pizzería.
- No puede ser asignado como empleado de otra cuenta; su rol es propio de su cuenta.

### 2.3 Administrador
Gestiona una pizzería específica con acceso completo a sus funciones operativas.
- Administra el catálogo de productos, combos y precios de su pizzería.
- Gestiona los usuarios (empleados) de su pizzería (alta, baja, cambio de rol).
- Accede a todos los reportes de su pizzería.
- No puede gestionar otras pizzerías de la misma cuenta (salvo que el Dueño le asigne ese rol en ellas también).

### 2.4 Cajero / Cobrador
- Ve todos los pedidos entrantes de su pizzería.
- Gestiona el estado de pago (confirmar pago en destino, transferencia).
- Puede marcar un pedido como "pagado".
- Crea pedidos telefónicos manuales.
- Atiende derivaciones HITL (Human in the Loop).
- Accede a reportes básicos de su pizzería.

### 2.5 Preparador / Cocinero
- Ve únicamente los pedidos en estado **Pendiente de Preparación** e **En Preparación** de su pizzería.
- Puede avanzar el estado de sus pedidos hacia **A Despacho**.
- No tiene acceso a datos de pago ni a reportes.

### 2.6 Repartidor / Delivery
- Ve los pedidos en estado **A Despacho** y **En Delivery** de su pizzería.
- Puede marcar un pedido como **Entregado** o reportar una incidencia.
- Puede ver la dirección de entrega del cliente.

---

## 2.7 Registro, Multi-tenancy y Múltiples WhatsApp

### Registro de cuenta y primera pizzería

El Dueño se registra una única vez en la plataforma. El flujo de alta es:

```
1. El Dueño accede a la página de registro
2. Completa sus datos de cuenta:
   · Nombre completo
   · Email (usado para login)
   · Contraseña
   · Teléfono de contacto
3. Completa los datos de su primera pizzería:
   · Nombre de la pizzería
   · Dirección / localidad
   · Logo (opcional)
4. Conecta el primer número de WhatsApp
   (escanea el QR de WPPConnect para vincular la sesión)
5. El sistema crea la cuenta, la pizzería y el panel listo para operar
6. El Dueño puede agregar empleados y configurar el menú
```

### Agregar una segunda pizzería (o más)

Desde su panel de cuenta, el Dueño puede crear nuevas pizzerías en cualquier momento. Cada pizzería tiene su propio:

- Menú y catálogo de productos
- Números de WhatsApp vinculados
- Equipo de empleados (usuarios del panel)
- Configuración del chatbot (mensajes de bienvenida, horarios, etc.)
- Historial de pedidos y clientes
- Reportes independientes

### Selector de pizzería en el panel

Cuando el Dueño o un empleado con acceso a más de una pizzería inicia sesión, el panel muestra un **selector de pizzería** antes de entrar al tablero. También puede cambiar de pizzería desde el menú principal sin cerrar sesión.

```
┌─────────────────────────────────────────────┐
│  Bienvenido, Alejandro                       │
│  ¿A qué pizzería querés acceder?             │
│                                             │
│  🍕 Pizzería Centro        [Entrar]          │
│     3 pedidos activos                        │
│                                             │
│  🍕 Pizzería Norte         [Entrar]          │
│     1 pedido activo                          │
│                                             │
│  [+ Agregar nueva pizzería]                  │
└─────────────────────────────────────────────┘
```

### Múltiples números de WhatsApp por pizzería

Una misma pizzería puede tener **más de un número de WhatsApp** vinculado (por ejemplo, un número principal y uno de respaldo, o números diferentes por zona de delivery).

| Aspecto                          | Comportamiento                                                             |
|----------------------------------|----------------------------------------------------------------------------|
| **Sesiones WPPConnect**          | Cada número tiene su propia sesión WPPConnect activa                       |
| **Panel unificado**              | Todos los pedidos de todos los números se ven en el mismo tablero          |
| **Identificación del cliente**   | El cliente se identifica por su propio número de WhatsApp, no por el número al que escribió |
| **Número de contacto visible**   | En el detalle del pedido se muestra a qué número de la pizzería escribió el cliente |
| **LLM compartido**               | El mismo chatbot y menú se usa para todos los números de esa pizzería      |
| **Reconocimiento cross-número**  | Si un cliente escribió al número A y luego escribe al número B de la misma pizzería, el sistema lo reconoce por su número propio |

### Gestión de números de WhatsApp

El Dueño (y el Administrador de esa pizzería) puede desde el panel:

- Ver el estado de cada sesión de WhatsApp (conectada / desconectada / escaneando QR).
- Agregar un nuevo número: genera un QR para escanear con el celular del número a vincular.
- Desactivar un número temporalmente sin desvincularlo.
- Eliminar un número (las conversaciones históricas se conservan).

### Aislamiento de datos entre pizzerías

Cada pizzería es un tenant completamente aislado. Los empleados de una pizzería no pueden ver ni acceder a los datos de otra, aunque pertenezcan al mismo Dueño. El Dueño es el único que tiene visibilidad cruzada.

| Dato                      | Alcance                                            |
|---------------------------|----------------------------------------------------|
| Pedidos                   | Por pizzería                                       |
| Clientes y sus datos      | Por pizzería (el mismo cliente puede existir en dos pizzerías del mismo dueño de forma independiente) |
| Menú y catálogo           | Por pizzería                                       |
| Empleados / usuarios      | Por pizzería                                       |
| Reportes estándar         | Por pizzería                                       |
| Reporte consolidado       | Solo accesible para el Dueño, muestra el total de todas sus pizzerías |

---

## 3. Inventario / Lista de Productos

El sistema mantiene un **registro maestro de productos** que centraliza todos los ítems disponibles (pizzas, empanadas y bebidas). Cada producto del inventario existe de forma independiente antes de ser categorizado con precios y variantes en el catálogo.

### 3.1 Atributos de cada producto en el inventario

| Atributo        | Tipo     | Descripción                                                                 |
|----------------|----------|-----------------------------------------------------------------------------|
| **Código / ID** | Texto único | Identificador alfanumérico corto del producto (ej: `PIZ-MOZ`, `EMP-CAR`, `BEB-COCA15`). Generado automáticamente o ingresado manualmente. No editable una vez creado. |
| **Nombre corto**| Texto    | Nombre breve para uso interno, etiquetas e impresión (ej: `Mozza`, `Carne suave`, `Coca 1.5L`). Máximo 30 caracteres. |
| **Nombre completo** | Texto | Nombre completo visible para el cliente en el chatbot (ej: `Pizza Mozzarella`, `Empanada de Carne Suave`). |
| **Descripción** | Texto largo | Detalle de los ingredientes o contenido del producto. Visible para el cliente al consultar el menú por WhatsApp. |
| **Categoría**   | Enum     | Pizza / Empanada / Bebida                                                   |
| **Disponible**  | Booleano | Si está activo y puede ser pedido. Se puede desactivar de forma temporal.   |
| **Fecha de alta** | Fecha  | Fecha en que fue creado en el sistema. Generada automáticamente.            |

### 3.2 Ejemplos de productos en el inventario

| Código     | Nombre corto     | Nombre completo             | Categoría | Descripción                                      |
|------------|------------------|-----------------------------|-----------|--------------------------------------------------|
| PIZ-MOZ    | Mozza            | Pizza Mozzarella            | Pizza     | Salsa de tomate, mozzarella, orégano             |
| PIZ-FUG    | Fugazzeta        | Pizza Fugazzeta             | Pizza     | Cebolla, mozzarella, aceitunas negras            |
| PIZ-NAP    | Napo             | Pizza Napolitana            | Pizza     | Salsa, tomate fresco, mozzarella, ajo            |
| EMP-CAR    | Carne suave      | Empanada de Carne Suave     | Empanada  | Carne picada, cebolla, pimiento, huevo           |
| EMP-POL    | Pollo            | Empanada de Pollo           | Empanada  | Pollo desmenuzado, morrón, queso cremoso         |
| EMP-JAQ    | Jamón y queso    | Empanada de Jamón y Queso   | Empanada  | Jamón cocido, queso mozzarella                   |
| BEB-COCA15 | Coca 1.5L        | Coca-Cola 1.5 litros        | Bebida    | Botella de Coca-Cola 1.5L                        |
| BEB-FAN06  | Fanta 600        | Fanta Naranja 600ml         | Bebida    | Botella de Fanta 600ml                           |

### 3.3 Reglas del inventario

- El **código** es único en todo el sistema y no puede repetirse entre categorías.
- Un producto no puede eliminarse si está referenciado en pedidos históricos; solo puede **desactivarse**.
- El código puede usarse como referencia interna para impresión de tickets, integración con otros sistemas o búsquedas rápidas en el panel.
- Los combos **no forman parte del inventario base**; se gestionan por separado en el catálogo de combos y se componen referenciando productos del inventario.

---

## 4. Catálogo de Productos

### 4.1 Pizzas

Cada pizza puede pedirse en dos tamaños: **Grande** o **Chica**. Adicionalmente existe la opción **Mitad y Mitad**, que permite combinar dos gustos distintos en una pizza grande.

El catálogo de pizzas extiende los productos del inventario con atributos de precio y tamaño.

| Atributo        | Descripción                                              |
|----------------|----------------------------------------------------------|
| Código / ID     | Referencia al producto en el inventario (ej: `PIZ-MOZ`)  |
| Nombre corto    | Nombre breve para tickets e interno                      |
| Nombre completo | Nombre del gusto visible para el cliente                 |
| Descripción     | Ingredientes principales (heredada del inventario)       |
| Precio Grande   | Precio para tamaño grande                                |
| Precio Chica    | Precio para tamaño chica                                 |
| Disponible      | Sí / No (para desactivar temporalmente)                  |

**Regla Mitad y Mitad**: El precio de una pizza mitad y mitad se calcula como el mayor de los dos precios de los gustos elegidos (tamaño grande), más un recargo opcional configurable.

### 4.2 Empanadas

Las empanadas se venden por unidad o por docena. Cada gusto es un producto individual del inventario.

| Atributo        | Descripción                                   |
|----------------|-----------------------------------------------|
| Código / ID     | Referencia al producto en el inventario (ej: `EMP-CAR`) |
| Nombre corto    | Nombre breve para tickets e interno           |
| Nombre completo | Gusto visible para el cliente                 |
| Descripción     | Detalle del relleno (heredada del inventario) |
| Precio unitario | Precio por unidad                             |
| Precio docena   | Precio por 12 unidades (puede tener descuento)|
| Disponible      | Sí / No                                       |

### 4.3 Bebidas

| Atributo        | Descripción                                     |
|----------------|-------------------------------------------------|
| Código / ID     | Referencia al producto en el inventario (ej: `BEB-COCA15`) |
| Nombre corto    | Nombre breve para tickets e interno             |
| Nombre completo | Nombre del producto visible para el cliente     |
| Descripción     | Presentación o detalle                          |
| Precio          | Precio unitario                                 |
| Disponible      | Sí / No                                         |

### 4.4 Combos

Los combos agrupan productos con un precio especial. Cada combo es configurable por el administrador y referencia productos del inventario.

| Atributo      | Descripción                                                                  |
|--------------|------------------------------------------------------------------------------|
| Código / ID   | Identificador del combo (ej: `CMB-FAM`, `CMB-NOCHE`)                        |
| Nombre corto  | Nombre breve para tickets (ej: `Combo Familiar`)                             |
| Nombre completo | Nombre visible para el cliente en el chatbot                               |
| Descripción   | Detalle de qué incluye el combo                                              |
| Contenido     | Lista de códigos de productos: una o más pizzas, empanadas y/o bebidas       |
| Precio combo  | Precio especial del combo                                                    |
| Disponible    | Sí / No                                                                      |

> **Nota**: El combo tiene precio fijo. Si el combo incluye una pizza, el cliente podrá elegir el gusto (dentro de los disponibles); si incluye mitad y mitad, se aplica la misma lógica de selección.

---

## 5. Flujo del Chatbot (WhatsApp)

### 5.1 Arquitectura conversacional basada en LLM

El chatbot no opera con un menú de opciones numeradas rígido. En su lugar, utiliza un **modelo de lenguaje (LLM)** como motor de conversación. El LLM recibe cada mensaje del cliente y decide de forma inteligente cómo responder, qué información ya tiene, qué le falta recolectar y cómo guiar la conversación hacia un pedido completo.

**n8n** actúa como orquestador: recibe el mensaje entrante desde WPPConnect, consulta el estado actual del cliente en la base de datos (historial de la conversación, pedido en curso, datos del cliente), construye el contexto para el LLM y envía la respuesta al cliente por WhatsApp.

```
  Cliente escribe por WhatsApp
           │
           ▼
    WPPConnect Server
           │  (webhook)
           ▼
          n8n
           │
           ├── Recupera estado de sesión del cliente (BD)
           ├── Recupera catálogo vigente (productos, precios, combos)
           ├── Recupera datos del cliente si ya existe (nombre, tel., dirección)
           │
           ▼
    LLM (con contexto completo)
           │
           ├── Interpreta el mensaje
           ├── Actualiza el pedido en curso (BD)
           ├── Detecta si el cliente está trabado → ofrece ayuda
           ├── Solicita datos faltantes (nombre, dirección, pago)
           │
           ▼
    Respuesta generada por el LLM
           │
           ▼
          n8n
           │
           ├── Ejecuta acciones si corresponde:
           │     · Registrar pedido confirmado
           │     · Generar link MercadoPago
           │     · Actualizar estado del pedido
           │
           ▼
    WPPConnect → mensaje enviado al cliente
```

### 5.2 Contexto que recibe el LLM en cada turno

En cada mensaje entrante, n8n construye un **prompt de sistema** que incluye:

- **Rol y personalidad**: el LLM sabe que es el asistente virtual de la pizzería, con un tono amigable y servicial.
- **Catálogo actualizado**: lista de pizzas, empanadas, bebidas y combos disponibles, con sus precios. Si un producto está desactivado, no se incluye en el contexto.
- **Datos del cliente**: nombre, teléfono y dirección guardados de pedidos anteriores (si existen), para evitar volver a pedirlos.
- **Pedido en curso**: ítems ya seleccionados en la conversación actual, con subtotales.
- **Historial reciente de la conversación**: últimos N mensajes para mantener coherencia.
- **Estado de la sesión**: en qué etapa está el cliente (eligiendo productos, confirmando, esperando pago, etc.).
- **Instrucciones de negocio**: reglas como el recargo de mitad y mitad, precio de docena de empanadas, horario de atención, etc.

### 5.3 Etapas de la conversación

El LLM guía al cliente de forma fluida a través de las siguientes etapas. No son pasos obligatorios en orden estricto; el cliente puede decir "quiero una mozza grande y seis empanadas de carne" en un solo mensaje y el LLM lo procesa todo de una vez.

#### Etapa 1 — Bienvenida e identificación
- Si el cliente es nuevo: el LLM lo saluda y le pregunta su nombre.
- Si el cliente ya tiene datos guardados: lo saluda por su nombre y retoma el contexto ("¡Hola Juan! ¿Querés hacer un pedido?").
- Si tiene un pedido activo en curso: le informa el estado actual.

#### Etapa 2 — Toma del pedido
El LLM comprende lenguaje natural. El cliente puede pedir productos de distintas formas:
- "Dame una mozza grande"
- "Quiero mitad napolitana, mitad fugazzeta"
- "¿Qué empanadas tienen?"
- "Poneme el combo familiar"
- "Agrego una Coca de 1.5"

El LLM interpreta, confirma lo entendido y actualiza el pedido. Si algo es ambiguo (ej: "una pizza" sin especificar tamaño), el LLM pregunta lo que necesita saber.

#### Etapa 3 — Recolección de datos del cliente
El LLM solicita de forma conversacional los datos necesarios si aún no los tiene:

| Dato         | Cuándo se solicita                                      |
|--------------|---------------------------------------------------------|
| **Nombre**   | Primera vez que el cliente interactúa                   |
| **Teléfono** | Se obtiene automáticamente del número de WhatsApp       |
| **Dirección**| Solo si el cliente elige delivery; se guarda para futuros pedidos |

Si el cliente ya tiene dirección guardada, el LLM la menciona y pregunta si la entrega es en la misma dirección o en otra.

#### Etapa 4 — Resumen y confirmación
Cuando el cliente indica que terminó de elegir (o el LLM infiere que el pedido está completo), presenta un resumen claro:

```
Acá está tu pedido, Juan:

🍕 1x Pizza Mozzarella Grande — $2.100
🥟 6x Empanada Carne Suave — $1.800
🥤 1x Coca-Cola 1.5L — $400

Total: $4.300
Entrega en: Av. Siempre Viva 742

¿Lo confirmamos así o querés cambiar algo?
```

#### Etapa 5 — Método de pago
Una vez confirmado el pedido, el LLM pregunta cómo quiere pagar:

```
¿Cómo preferís pagar?

1. 💳 MercadoPago (te mando el link ahora)
2. 💵 Efectivo al momento de la entrega
3. 🏦 Transferencia bancaria
```

Según la respuesta:
- **MercadoPago**: n8n genera el link y el LLM lo envía en el siguiente mensaje.
- **Efectivo**: el pedido pasa directamente a preparación.
- **Transferencia**: el LLM envía los datos bancarios y el pedido pasa a preparación; el cajero confirma el pago desde el panel.

#### Etapa 6 — Confirmación final
El LLM confirma el pedido con el número asignado y le avisa al cliente que recibirá actualizaciones de estado.

### 5.4 Detección de cliente trabado

El LLM detecta situaciones donde el cliente parece confundido o no avanza, y actúa proactivamente:

| Situación detectada                              | Acción del LLM                                          |
|--------------------------------------------------|---------------------------------------------------------|
| Mensaje fuera de contexto o irrelevante          | Reencuadra amablemente hacia el pedido                  |
| Pregunta sobre un producto que no existe         | Explica que no está disponible y sugiere alternativas   |
| El cliente lleva varios mensajes sin agregar nada al pedido | Ofrece ayuda: "¿Te cuento qué tenemos hoy?" |
| Respuesta ambigua (ej: "la de siempre")          | Consulta el historial y propone el último pedido        |
| El cliente escribe solo "hola" o "?" sin contexto | Saluda y presenta brevemente el menú               |
| Silencio prolongado seguido de un mensaje        | Retoma sin presuponer, pregunta si quiere continuar el pedido anterior |
| Error de escritura en nombre de producto         | Intenta interpretar y confirma: "¿Querés decir Fugazzeta?" |
| Consulta sobre crédito disponible                | Consulta la BD y responde con el saldo exacto              |

El LLM **nunca corta la conversación ni da error**. Si no entiende algo, lo dice con naturalidad y pide aclaración.

### 5.5 Datos del cliente — Modelo de almacenamiento

n8n persiste los datos del cliente en la base de datos. Estos datos se reutilizan en pedidos futuros.

| Campo          | Origen                                      | Editable por el cliente |
|----------------|---------------------------------------------|-------------------------|
| Teléfono       | Número de WhatsApp (automático)             | No                      |
| Nombre         | Primer pedido (el LLM lo pregunta)          | Sí, en cualquier momento |
| Dirección      | Primer pedido con delivery                  | Sí, por mensaje o al confirmar |
| Último pedido  | Se guarda automáticamente al confirmar      | No (es histórico)       |
| Fecha de alta  | Primer contacto                             | No                      |

El cliente puede actualizar su nombre o dirección en cualquier momento simplemente diciéndolo en el chat ("mi dirección cambió, ahora es...") y el LLM actualiza el registro.

### 5.6 Cierre de sesión por inactividad

Si el cliente tiene un pedido **en curso** (aún no confirmado) y no envía ningún mensaje durante **10 minutos**, n8n dispara un temporizador que activa el siguiente flujo:

```
Cliente no responde por 10 minutos
            │
            ▼
  n8n detecta inactividad
            │
            ▼
  LLM envía mensaje de consulta:
  "¡Hola! ¿Seguís por acá? Tenés estos
   productos en tu pedido: [resumen].
   Si querés continuar, escribime.
   Si no, cerramos la sesión."
            │
            ▼
  Espera 5 minutos más
       /        \
  Responde     No responde
      │              │
      ▼              ▼
  Retoma      Se cierra la sesión:
  pedido      · El pedido en curso se descarta
              · El estado de sesión se limpia
              · Se guarda registro del intento fallido
```

**Reglas del cierre de sesión:**

| Condición                        | Comportamiento                                                      |
|----------------------------------|---------------------------------------------------------------------|
| Inactividad ≥ 10 min (pedido en curso) | n8n envía mensaje de consulta vía LLM                      |
| Cliente responde dentro de 5 min | Retoma la sesión con el pedido intacto                             |
| No responde en 5 min adicionales | Sesión cerrada, pedido descartado                                  |
| Pedido ya confirmado (cualquier estado) | No aplica: las notificaciones de estado siguen funcionando |
| Cliente escribe después del cierre | El LLM lo recibe como una nueva conversación, sin pedido activo  |

> **Nota**: el temporizador es gestionado por n8n mediante un nodo de espera o un job programado que verifica la marca de tiempo del último mensaje del cliente comparado con el momento actual.

### 5.7 Notificaciones automáticas al cliente

Estas notificaciones las envía n8n directamente (no el LLM), al detectar cambios de estado del pedido:

| Evento                                    | Mensaje enviado al cliente                                              |
|-------------------------------------------|-------------------------------------------------------------------------|
| Pedido confirmado                         | "Tu pedido #XXX fue recibido. ¡Estamos en eso!"                        |
| Link de pago enviado                      | "Podés pagar tu pedido acá: [link MercadoPago]"                         |
| Pago confirmado                           | "¡Recibimos tu pago! Tu pedido pasa a preparación."                     |
| Pedido en preparación                     | "¡Tu pedido está siendo preparado! 🍕"                                  |
| Pedido listo — **delivery**               | "Tu pedido está listo y ya salió para entregarte. ¡En camino!"          |
| Pedido listo — **retiro en local**        | "Tu pedido está listo para retirar. ¡Te esperamos!"                     |
| Pedido en camino *(solo delivery)*        | "Tu pedido está en camino. ¡Ya llega!"                                  |
| Pedido entregado                          | "¡Tu pedido fue entregado! Gracias por elegirnos. 🎉"                   |
| Pedido cancelado — sin cargo              | "Tu pedido #XXX fue cancelado. No se realizó ningún cobro."             |
| Pedido cancelado — con crédito            | "Tu pedido #XXX fue cancelado. Tenés un crédito de $X para tu próximo pedido." |
| Incidencia — pedido en revisión           | "Tuvimos un inconveniente con tu pedido #XXX. Estamos resolviéndolo y te avisamos pronto." |
| Re-despacho iniciado                      | "Tu pedido está siendo re-enviado. Disculpá el inconveniente."          |
| Derivado a operador humano                | "En un momento te atiende una persona de nuestro equipo."               |
| Operador finalizó la atención             | "¡Listo! Tu pedido quedó confirmado. Te avisamos cuando esté en camino." |

---

## 5.8 Transferencia a Operador Humano (Human in the Loop)

### Concepto general

Cuando el cliente solicita hablar con una persona — o cuando el LLM detecta que la situación lo requiere — la conversación entra en modo **derivación humana**: el LLM se pausa, un operador del panel toma el control del chat vía WhatsApp y, si corresponde, puede terminar de cargar el pedido directamente desde el backoffice.

Este patrón se conoce como **HITL (Human in the Loop)** y es el estándar en sistemas conversacionales de nivel productivo.

### Cuándo se activa la derivación

| Disparador                                                                           | Origen          |
|--------------------------------------------------------------------------------------|-----------------|
| El cliente escribe "quiero hablar con una persona", "llamame", "necesito ayuda" o similar | Cliente    |
| El LLM detecta frustración reiterada o un problema que no puede resolver             | LLM (automático)|
| El operador decide tomar el control desde el panel, sin que el cliente lo haya pedido | Operador      |

### Flujo completo de derivación

```
Cliente pide hablar con una persona
              │
              ▼
       LLM reconoce la intención
              │
              ▼
  LLM responde y se pausa:
  "Entendido. En un momento te atiende
   alguien de nuestro equipo. Tu pedido
   queda guardado mientras tanto."
              │
              ▼
  n8n cambia estado de sesión → DERIVADO A OPERADOR
              │
              ├── Guarda el pedido en curso (ítems, datos del cliente)
              ├── Registra timestamp de la derivación
              └── Envía alerta al panel web (Cajero y Admin)
              │
              ▼
       ¿Hay operador disponible?
       /                       \
      Sí                        No
      │                          │
      ▼                          ▼
  Operador                n8n espera X minutos
  acepta la               (configurable). Si nadie
  atención                acepta, el LLM retoma:
      │                   "Por ahora no hay nadie
      │                    disponible. ¿Querés que
      │                    te siga ayudando yo?"
      │
      ▼
  LLM queda SUSPENDIDO para ese cliente.
  Mensajes entrantes se muestran en el panel
  pero el bot NO responde automáticamente.
      │
      ▼
  Operador atiende desde el panel
      │
      ▼
  Operador marca "Finalizar atención"
      │
      ├── Pedido confirmado desde el panel
      │     → Estado del pedido avanza normalmente
      │     → LLM retoma solo como notificador
      │
      └── Pedido no concretado
            → "Devolver al bot": LLM retoma con contexto guardado
            → "Cerrar sin pedido": sesión finalizada, pedido descartado
```

### Qué puede hacer el operador desde el panel durante la derivación

El panel muestra una sección **"Conversaciones activas"** que lista todas las derivaciones en curso, ordenadas por tiempo de espera. En cada conversación el operador dispone de:

- **Historial completo del chat** con el cliente, incluyendo la interacción previa con el LLM.
- **Pedido en curso** tal como estaba al derivarse: ítems seleccionados, subtotales y datos del cliente ya cargados.
- **Campo de texto para responder**: el operador escribe y envía mensajes al cliente directamente por WhatsApp desde el panel (n8n los despacha vía WPPConnect).
- **Editor de pedido**: puede agregar o quitar productos, cambiar cantidades y variantes usando el mismo catálogo.
- **Botón "Confirmar pedido"**: cierra el pedido desde el panel, genera el cobro si corresponde y lo envía a cocina.
- **Botón "Finalizar atención"**: marca la derivación como resuelta y define qué sucede a continuación (devolver al bot o cerrar).

### Estado de la sesión de conversación

El estado de la **sesión de conversación** es independiente del estado del pedido y agrega los siguientes valores:

| Estado de sesión            | Descripción                                                          |
|-----------------------------|----------------------------------------------------------------------|
| **Activa — bot**            | El LLM está atendiendo normalmente.                                  |
| **En espera de operador**   | Se solicitó derivación pero ningún operador la aceptó todavía.       |
| **Derivada — humano**       | Un operador tomó el control. El LLM está suspendido.                 |
| **Cerrada**                 | La sesión finalizó (pedido confirmado, descartado o por inactividad).|

El estado del pedido en curso **no cambia** por la derivación en sí; solo se modifica cuando el operador o el bot ejecutan acciones concretas sobre él.

### Comportamiento del temporizador de inactividad durante la derivación

El temporizador de 10 minutos (sección 5.6) **se suspende** automáticamente mientras la sesión está en estado "En espera de operador" o "Derivada — humano". El timer se reactiva únicamente si el operador devuelve el control al bot.

### Permisos por rol

| Acción                                          | Cajero | Cocinero | Repartidor | Admin |
|-------------------------------------------------|--------|----------|------------|-------|
| Ver alertas de derivación entrantes             | ✅     | ❌       | ❌         | ✅    |
| Aceptar y atender una derivación                | ✅     | ❌       | ❌         | ✅    |
| Enviar mensajes al cliente por WhatsApp         | ✅     | ❌       | ❌         | ✅    |
| Editar y confirmar el pedido en curso           | ✅     | ❌       | ❌         | ✅    |
| Devolver el control al bot                      | ✅     | ❌       | ❌         | ✅    |
| Tomar control sin que el cliente lo haya pedido | ❌     | ❌       | ❌         | ✅    |

---

## 6. Estados de un Pedido

### 6.1 Diagrama completo de estados

```
PEDIDO EN CURSO ──── (inactividad + sin respuesta) ──► DESCARTADO
     │
     ▼ (cliente confirma)
PENDIENTE DE PAGO ─── (pago online) ──► espera webhook MercadoPago
     │    │                                        │
     │    │ (cancelación antes del pago)            │ (pago recibido)
     │    ▼                                        ▼
     │  CANCELADO          PENDIENTE DE PREPARACIÓN
     │                              │
     │ (efectivo / transferencia)   │ (cancelación antes de preparar)
     ▼                              │──────────────► CANCELADO
EN PREPARACIÓN ◄───────────────────┘
     │
     │ (cancelación durante preparación → según política)
     ├─────────────────────────────────────────────► CANCELADO
     │
     ▼ (cocinero termina)
A DESPACHO
     │
     ▼ (repartidor toma el pedido)
EN DELIVERY
     │        │
     │        │ (repartidor reporta incidencia)
     │        ▼
     │   CON INCIDENCIA ─── (admin decide) ──► CANCELADO
     │        │                         └────► RE-DESPACHO ──► EN DELIVERY
     │
     ▼ (entrega confirmada)
ENTREGADO  (estado final normal)
```

### 6.2 Descripción de estados

| Estado                       | Descripción                                                                          |
|------------------------------|--------------------------------------------------------------------------------------|
| **Pedido en curso**          | El cliente está armando su pedido en el chatbot. Aún no confirmado.                  |
| **Pendiente de pago**        | Pedido confirmado, link de MercadoPago enviado. Esperando confirmación del pago.     |
| **Pendiente de preparación** | Pago online confirmado. El pedido espera ser tomado por cocina.                      |
| **En preparación**           | El cocinero tomó el pedido. Está siendo preparado.                                   |
| **A despacho**               | El pedido está listo. Espera que el repartidor lo retire (o el cliente lo pase a buscar). |
| **En delivery**              | El repartidor tomó el pedido y está en camino al cliente.                            |
| **Entregado**                | El pedido llegó correctamente al cliente. Estado final exitoso.                      |
| **Cancelado**                | El pedido fue cancelado. Puede tener sub-estado de pago: sin cargo, con crédito o con reembolso. |
| **Con incidencia**           | Se reportó un problema durante o después del delivery (entrega incorrecta, pedido equivocado, etc.). Requiere resolución manual. |
| **Descartado**               | El pedido en curso fue cerrado automáticamente por inactividad. No llegó a confirmarse. |

### 6.3 Estado de pago (campo independiente)

| Estado de pago           | Descripción                                                                  |
|--------------------------|------------------------------------------------------------------------------|
| **Pagado**               | El pago fue confirmado (online o cajero marcó pago recibido).                |
| **A pagar en destino**   | El cliente eligió pagar en efectivo al momento de la entrega.                |
| **Pendiente de pago**    | Se envió link de MercadoPago pero aún no se recibió confirmación.            |
| **Crédito a favor**      | El pedido fue cancelado y el monto queda acreditado para una próxima compra. |
| **Reembolsado**          | El monto fue devuelto al cliente (requiere acción manual del administrador).  |
| **Sin cargo**            | El pedido fue cancelado antes de generar cualquier cobro.                    |

---

## 6.4 Política de Cancelaciones

### ¿Quién puede cancelar?

| Rol           | Puede cancelar                              | Restricción                                        |
|---------------|---------------------------------------------|----------------------------------------------------|
| **Cliente**   | Solo vía WhatsApp (le avisa al LLM)         | Solo mientras el pedido no esté en preparación     |
| **Cajero**    | Desde el panel web                          | En cualquier estado excepto Entregado              |
| **Admin**     | Desde el panel web                          | En cualquier estado excepto Entregado              |
| **Cocinero**  | No puede cancelar                           | —                                                  |
| **Repartidor**| No puede cancelar directamente; solo reportar incidencia | —                                    |

### Reglas según el momento de la cancelación

| Momento de la cancelación                | Política de pago                                                            |
|------------------------------------------|-----------------------------------------------------------------------------|
| Antes de confirmar el pedido             | Sin cargo. El cliente nunca fue cobrado.                                    |
| Confirmado, pendiente de pago (MP)       | Sin cargo. El link de pago se invalida (se cancela la preferencia en MP).   |
| Pago online recibido, aún no preparado   | **Crédito a favor** por el monto total, aplicable al siguiente pedido. O reembolso manual si el cliente lo solicita, a criterio del administrador. |
| Ya en preparación                        | **Crédito a favor** por el monto total. El costo de los ingredientes ya fue incurrido, por lo que no se reembolsa en efectivo salvo decisión del admin. |
| En delivery o entregado                  | No se admite cancelación. Se gestiona como incidencia si hay problema.      |

> **Nota de negocio**: la política de crédito vs reembolso es una decisión del negocio. Esta especificación propone crédito como opción predeterminada, pero el administrador puede optar por reembolso manual en casos justificados.

### Flujo de cancelación solicitada por el cliente vía WhatsApp

```
Cliente escribe "quiero cancelar mi pedido"
              │
              ▼
        LLM identifica la intención de cancelar
              │
              ├── Pedido en curso o pendiente de pago
              │     → LLM cancela y confirma "Sin cargo"
              │
              ├── Pago recibido / en preparación
              │     → LLM informa: "Tu pedido ya fue pagado/está en preparación.
              │       Si cancelás, te queda un crédito de $X para tu próximo
              │       pedido. ¿Confirmás la cancelación?"
              │           │ Sí → n8n aplica cancelación + crédito
              │           │ No → LLM retoma el pedido normal
              │
              └── En delivery o entregado
                    → LLM informa que no es posible cancelar en este estado
                      y ofrece reportar una incidencia si hubo un problema
```

### Crédito a favor — comportamiento

- El crédito queda asociado al número de WhatsApp del cliente en la base de datos.
- El LLM lo detecta automáticamente en el siguiente pedido y lo aplica al total antes de mostrar el resumen.
- El crédito no vence (configurable por el administrador).
- El administrador puede ver y gestionar créditos desde el panel.

### Consulta de crédito disponible vía WhatsApp

El cliente puede preguntarle al LLM en cualquier momento cuánto crédito tiene disponible. El LLM consulta la base de datos y responde:

| Situación                    | Respuesta del LLM                                                      |
|------------------------------|------------------------------------------------------------------------|
| Tiene crédito disponible     | "Tenés un crédito de **$X** a favor, que se va a aplicar automáticamente en tu próximo pedido." |
| No tiene crédito             | "No tenés ningún crédito a favor en este momento."                     |
| Tiene crédito y está pidiendo| Lo informa en el resumen del pedido antes de confirmar: "Se aplicó tu crédito de $X. Total a pagar: $Y." |

Ejemplos de mensajes que el LLM reconoce como consulta de crédito:
- "¿Cuánto crédito tengo?"
- "¿Me quedó plata de la última cancelación?"
- "¿Tengo saldo a favor?"
- "¿Qué pasó con mi reembolso?"

---

## 6.5 Gestión de Incidencias

Las incidencias cubren situaciones excepcionales que ocurren **durante o después del delivery**: entrega en dirección incorrecta, pedido equivocado, producto faltante, o cualquier inconveniente que requiera intervención del equipo.

### Tipos de incidencia

| Tipo                          | Descripción                                                               |
|-------------------------------|---------------------------------------------------------------------------|
| **Entrega en dirección incorrecta** | El repartidor entregó en un domicilio que no corresponde al pedido.  |
| **Pedido equivocado**         | El cliente recibió productos que no corresponden a su orden.              |
| **Producto faltante**         | Falta uno o más ítems del pedido entregado.                               |
| **Pedido en mal estado**      | El producto llegó dañado, frío, o en condiciones inaceptables.            |
| **Cliente no encontrado**     | El repartidor llegó a la dirección pero no encontró al cliente.           |
| **Otro**                      | Cualquier problema no categorizado; requiere descripción manual.          |

### Quién puede reportar una incidencia

- **Repartidor**: desde el panel web, al marcar "Reportar problema" en lugar de "Entregado".
- **Cajero / Admin**: desde el panel web, en el detalle del pedido.
- **Cliente**: vía WhatsApp, al comunicárselo al LLM ("no me llegó el pedido", "me trajeron otra cosa", etc.). El LLM lo registra como incidencia y notifica al equipo.

### Flujo de re-despacho (entrega incorrecta)

```
Repartidor reporta "Entregué en dirección equivocada"
                    │
                    ▼
         Pedido pasa a estado: CON INCIDENCIA
                    │
                    ▼
         Admin / Cajero recibe alerta en el panel
                    │
                    ▼
           Admin evalúa la situación
          /                          \
   Re-despachar                   Cancelar / Compensar
         │                               │
         ▼                               ▼
  Se crea un nuevo                Cancelación con
  registro de despacho:           crédito o reembolso
  · Mismo pedido #XXX             según decisión del admin
  · Repartidor asignado
    (mismo u otro)
  · Dirección corregida
    si fue error de sistema
         │
         ▼
  Estado → EN DELIVERY (nuevo intento)
         │
         ▼
  Repartidor confirma entrega correcta
         │
         ▼
  Estado → ENTREGADO
  (el historial del pedido queda con el registro
   de la incidencia y el re-despacho)
```

### Flujo de incidencia reportada por el cliente vía WhatsApp

```
Cliente escribe "no me llegó el pedido" / "me trajeron otra pizza"
                    │
                    ▼
          LLM identifica la incidencia
                    │
                    ▼
          LLM registra la incidencia en el pedido
          y responde: "Entendemos el inconveniente.
          Ya avisamos al equipo y te vamos a
          contactar a la brevedad."
                    │
                    ▼
          n8n envía alerta al panel web
          (Admin / Cajero recibe notificación)
                    │
                    ▼
          Admin resuelve desde el panel:
          re-despacho, crédito o reembolso
```

### Impacto de las incidencias en reportes

Cada incidencia queda registrada con: tipo, pedido asociado, quién la reportó, fecha/hora, y resolución aplicada. Esto alimenta el reporte de incidencias (ver sección 10.6).

### Acciones disponibles por rol para incidencias

| Acción                              | Cajero | Cocinero | Repartidor | Admin |
|-------------------------------------|--------|----------|------------|-------|
| Reportar incidencia                 | ✅     | ❌       | ✅         | ✅    |
| Ver incidencias activas             | ✅     | ❌       | ✅*        | ✅    |
| Resolver incidencia (re-despacho)   | ✅     | ❌       | ❌         | ✅    |
| Aplicar crédito / reembolso         | ❌     | ❌       | ❌         | ✅    |
| Cancelar pedido con incidencia      | ✅     | ❌       | ❌         | ✅    |

*El repartidor solo ve las incidencias de sus propios pedidos.

---

## 7. Flujo de Pago

### 7.1 Pago Online con MercadoPago

```
1. Cliente confirma pedido y elige "Pagar ahora"
2. n8n genera una preferencia de pago en MercadoPago (monto = total del pedido)
3. MercadoPago devuelve un link de pago (checkout)
4. n8n envía el link al cliente por WhatsApp
5. Cliente accede al link y realiza el pago
6. MercadoPago envía webhook de confirmación a n8n
7. n8n actualiza el pedido:
   - Estado de pago → Pagado
   - Estado del pedido → Pendiente de preparación
8. El bot notifica al cliente que el pago fue recibido
9. El panel web notifica al cocinero del nuevo pedido
```

### 7.2 Pago en Efectivo o Transferencia

```
1. Cliente confirma pedido y elige "Efectivo en destino" o "Transferencia"
2. El pedido pasa directamente a estado → En Preparación
3. El bot notifica al cliente que el pedido está en preparación
4. Si elige transferencia, el bot puede enviar los datos bancarios
5. El cajero, al recibir la transferencia o el efectivo, marca el pedido como "Pagado"
   desde el panel web
```

---

## 8. Aplicación Web — Panel de Gestión

### 8.1 Acceso y Autenticación

El panel requiere usuario y contraseña. Cada usuario tiene un rol asignado por el administrador. La sesión expira tras un período de inactividad configurable.

### 8.2 Vista Principal — Tablero de Pedidos

La vista principal muestra todos los pedidos activos ordenados por orden de llegada (más antiguo primero), en formato de tarjetas tipo Kanban o lista.

**Filtros disponibles:**
- Por estado del pedido
- Por método de pago
- Por repartidor asignado
- Por rango de fecha/hora

**Información visible en cada tarjeta de pedido:**

- Número de pedido
- Nombre / número de WhatsApp del cliente
- Hora de recepción
- Resumen de productos
- Total del pedido
- Estado actual
- Estado de pago
- Tipo de entrega (delivery / retiro)

**Acciones disponibles por rol:**

| Acción                              | Cajero | Cocinero | Repartidor | Admin |
|-------------------------------------|--------|----------|------------|-------|
| Ver todos los pedidos               | ✅     | ✅*      | ✅*        | ✅    |
| Avanzar estado del pedido           | ✅     | ✅       | ✅         | ✅    |
| Marcar como pagado                  | ✅     | ❌       | ❌         | ✅    |
| Asignar repartidor                  | ✅     | ❌       | ❌         | ✅    |
| Cancelar pedido                     | ✅     | ❌       | ❌         | ✅    |
| Ver datos de entrega                | ✅     | ✅       | ✅         | ✅    |
| Reportar incidencia                 | ✅     | ❌       | ✅         | ✅    |
| Resolver incidencia / re-despacho   | ✅     | ❌       | ❌         | ✅    |
| Aplicar crédito o reembolso         | ❌     | ❌       | ❌         | ✅    |
| Ver y gestionar créditos de clientes| ❌     | ❌       | ❌         | ✅    |
| Crear pedido telefónico manual      | ✅     | ❌       | ❌         | ✅    |

*El cocinero solo ve pedidos en estados Pendiente de Preparación y En Preparación. El repartidor solo ve A Despacho, En Delivery y Con Incidencia de sus pedidos.

### 8.3 Vista de Detalle de Pedido

Al hacer clic en un pedido se abre una vista de detalle que muestra:

- Todos los datos del pedido
- Origen del pedido (WhatsApp / Telefónico)
- Timeline del historial de estados con fecha y hora
- Botones para avanzar al siguiente estado (según el rol)
- Notas internas (campo de texto libre visible solo para el personal)

---

### 8.4 Pedido Telefónico — Carga Manual desde el Panel

El operador (Cajero o Admin) puede registrar pedidos recibidos por teléfono directamente desde el panel, sin que el cliente haya interactuado con el chatbot. El flujo de estados del pedido es idéntico al de un pedido por WhatsApp.

#### Flujo de carga

```
Operador recibe llamada telefónica
              │
              ▼
  Abre el panel → [+ Nuevo pedido telefónico]
              │
              ▼
  Paso 1 — Identificación del cliente
  ┌─────────────────────────────────┐
  │  Buscar por teléfono            │
  │  ¿El cliente ya existe en BD?   │
  │   Sí → carga sus datos          │
  │   No → ingresa manualmente:     │
  │     · Nombre                    │
  │     · Teléfono                  │
  │     · Dirección (si es delivery)│
  │     · ¿Tiene WhatsApp? Sí / No  │
  └─────────────────────────────────┘
              │
              ▼
  Paso 2 — Armado del pedido
  (mismo catálogo que el chatbot:
   pizzas, empanadas, bebidas, combos)
              │
              ▼
  Paso 3 — Tipo de entrega
  Delivery / Retiro en local
              │
              ▼
  Paso 4 — Método de pago
  Efectivo / Transferencia / MercadoPago
              │
              ▼
  Paso 5 — Confirmar pedido
  El pedido entra al flujo normal de estados
```

#### Comportamiento según si el cliente tiene WhatsApp

| Situación | Comportamiento |
|-----------|----------------|
| **Tiene WhatsApp y ya existe en el sistema** | El número de teléfono vincula automáticamente al cliente. Las notificaciones de estado le llegan por WhatsApp igual que a cualquier pedido. Si en el futuro escribe por WhatsApp, el sistema ya tiene todos sus datos. |
| **Tiene WhatsApp pero es nuevo en el sistema** | Se crea el perfil del cliente con los datos ingresados por el operador. Las notificaciones de estado se envían por WhatsApp desde ese momento. Si escribe por WhatsApp en el futuro, el sistema lo reconoce. |
| **No tiene WhatsApp** | No se envían notificaciones automáticas. El operador es responsable de informar al cliente sobre el estado de su pedido (por teléfono). El perfil queda guardado con el flag `sin_whatsapp = true` para evitar intentar enviarle mensajes. |

#### Datos del cliente guardados para futuras interacciones

Independientemente del canal de origen (teléfono o WhatsApp), los datos del cliente se unifican en un único registro en la base de datos, usando el número de teléfono como clave:

| Campo              | Fuente                          | Reutilizable |
|--------------------|---------------------------------|--------------|
| Nombre             | Ingresado por el operador       | ✅ Sí        |
| Teléfono           | Ingresado por el operador       | ✅ Sí (clave)|
| Dirección          | Ingresada por el operador       | ✅ Sí        |
| Tiene WhatsApp     | Ingresado por el operador       | ✅ Sí        |
| Crédito a favor    | Calculado por el sistema        | ✅ Sí        |
| Historial de pedidos | Todos los pedidos del cliente | ✅ Sí        |

Si el cliente llama por primera vez y luego escribe por WhatsApp con el mismo número, el sistema lo reconoce automáticamente: el LLM lo saluda por su nombre y tiene acceso a su dirección y su historial.

#### Origen del pedido — campo adicional

Cada pedido registra su **canal de origen**:

| Valor         | Descripción                                      |
|---------------|--------------------------------------------------|
| `whatsapp`    | Pedido iniciado por el cliente via chatbot       |
| `telefónico`  | Pedido cargado manualmente por el operador       |
| `operador`    | Pedido completado por un operador en derivación HITL |

Este campo es visible en el detalle del pedido y en los reportes, permitiendo analizar la distribución de pedidos por canal.

---

## 9. ABM de Menú, Precios e Inventario

Accesible solo para el rol **Administrador**. Permite gestionar tanto el inventario base de productos como el catálogo de precios y variantes, sin necesidad de modificar código.

### 9.1 Gestión del Inventario (Lista de Productos)

Esta sección es el punto de entrada para cualquier producto nuevo. Antes de configurar precios, un producto debe existir en el inventario.

- Ver la lista completa de todos los productos registrados (pizzas, empanadas, bebidas) con su código, nombre corto y descripción.
- Crear un nuevo producto: se ingresa código, nombre corto, nombre completo, descripción y categoría.
- Editar nombre corto, nombre completo y descripción de un producto existente. El código no es editable una vez creado.
- Desactivar un producto (no se puede eliminar si tiene pedidos asociados).
- Buscar y filtrar por código, nombre o categoría.

### 9.2 Gestión de Pizzas
- Crear / editar / desactivar gustos de pizza vinculados al inventario.
- Definir precio para tamaño grande y chica.
- Configurar recargo para pizza mitad y mitad.
- Reordenar el listado que ve el cliente.

### 9.3 Gestión de Empanadas
- Crear / editar / desactivar gustos de empanada vinculados al inventario.
- Definir precio unitario y precio por docena.
- Marcar disponibilidad diaria (ej: "hoy no hay carne").

### 9.4 Gestión de Bebidas
- Crear / editar / desactivar bebidas vinculadas al inventario.
- Definir precio y tamaño.

### 9.5 Gestión de Combos
- Crear / editar / desactivar combos.
- Seleccionar los productos incluidos referenciando códigos del inventario.
- Establecer precio especial del combo.
- Definir si el combo permite personalización (ej: elegir gusto de pizza).

### 9.6 Configuración General
- Horarios de atención (el chatbot puede avisarle al cliente si está fuera de horario).
- Mensaje de bienvenida del chatbot.
- Mensaje de cierre (fuera de horario).
- Recargo por delivery (opcional, configurable por zona o precio fijo).
- Datos bancarios para transferencia.

---

## 10. Reportes

Accesibles para **Cajero** (básico) y **Administrador** (completo).

### 10.1 Reporte de Ventas Diarias
- Total recaudado en el día.
- Cantidad de pedidos por estado de pago (pagado / pendiente / a pagar en destino).
- Desglose por método de pago (MercadoPago / efectivo / transferencia).

### 10.2 Reporte de Productos Más Vendidos
- Ranking de pizzas, empanadas y bebidas por cantidad de unidades vendidas.
- Filtro por período (día / semana / mes).

### 10.3 Reporte de Combos
- Cuántas veces se pidió cada combo.
- Comparativa de ingresos: combos vs productos individuales.

### 10.4 Reporte de Tiempos
- Tiempo promedio entre recepción del pedido y entrega.
- Tiempo promedio en cada etapa (en preparación, en delivery, etc.).

### 10.5 Reporte de Delivery
- Pedidos por repartidor.
- Tiempo promedio de entrega por repartidor.

### 10.6 Reporte de Cancelaciones
- Cantidad de pedidos cancelados por período (día / semana / mes).
- Desglose por motivo: cancelación del cliente, cancelación del operador, tiempo de inactividad.
- Desglose por momento: antes del pago, tras el pago, durante preparación.
- Monto total de créditos generados vs reembolsos realizados.
- Créditos vigentes pendientes de uso por cliente.

### 10.7 Reporte de Incidencias
- Cantidad de incidencias por período.
- Desglose por tipo: entrega incorrecta, pedido equivocado, producto faltante, cliente no encontrado, etc.
- Incidencias por repartidor (útil para detectar patrones de error).
- Tiempo promedio de resolución de incidencias.
- Tasa de re-despacho exitoso vs cancelación tras incidencia.

---

## 11. Integraciones

### 11.1 WPPConnect Server
Servidor local que gestiona la sesión de WhatsApp y expone una API REST. n8n se conecta a este servidor para:
- Escuchar mensajes entrantes (webhook).
- Enviar mensajes de texto y mensajes con botones de respuesta rápida.
- Identificar al cliente por su número de teléfono.

### 11.2 n8n
Plataforma de automatización que actúa como el cerebro del sistema:
- Recibe los eventos de WPPConnect (mensaje nuevo).
- Determina el estado de la conversación de ese cliente.
- Ejecuta la lógica de negocio (armado del pedido, cálculo de precios).
- Persiste el estado de pedidos en base de datos.
- Llama a la API de MercadoPago para generar links de pago.
- Recibe el webhook de confirmación de pago de MercadoPago.
- Notifica a los operadores del panel web (vía WebSockets o actualización en base de datos).

### 11.3 MercadoPago
Integración mediante la API de Checkout Pro de MercadoPago:
- n8n crea una **preferencia de pago** con el total del pedido, descripción y datos del cliente.
- MercadoPago retorna una URL de pago.
- Al completarse el pago, MercadoPago llama al **webhook de notificación** (IPN/Webhook) configurado en n8n.
- n8n verifica el pago y actualiza el estado del pedido.

---

## 12. Wireframes de Pantallas Principales

### 12.1 Pantalla de Login

```
┌─────────────────────────────────────────┐
│                                         │
│          🍕 Pizzería Panel              │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │  Usuario                        │   │
│   └─────────────────────────────────┘   │
│   ┌─────────────────────────────────┐   │
│   │  Contraseña                     │   │
│   └─────────────────────────────────┘   │
│                                         │
│        [ Ingresar al panel ]            │
│                                         │
└─────────────────────────────────────────┘
```

---

### 12.2 Tablero Principal de Pedidos

```
┌──────────────────────────────────────────────────────────────────────────┐
│  🍕 Panel Pizzería   [Pedidos] [Menú] [Reportes] [Config]     👤 Admin ▼ │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PEDIDOS EN TIEMPO REAL                    🔴 3 nuevos   [🔄 Actualizar] │
│                                                                          │
│  Filtros: [Estado ▼] [Pago ▼] [Tipo ▼]       Buscar: [_____________]    │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ #  │ Cliente         │ Hora   │ Productos       │ Total │ Estado     │ │
│ ├──────────────────────────────────────────────────────────────────────┤ │
│ │ 42 │ Juan Pérez      │ 20:15  │ 1 Mozza grande  │ $3200 │🟡 Pend.Prep│ │
│ │    │ 11-1234-5678    │        │ 2x Carne Suave  │       │  💳 Pagado │ │
│ │    │                 │        │ 1 Coca 1.5L     │       │[Ver detalle]│
│ ├──────────────────────────────────────────────────────────────────────┤ │
│ │ 41 │ María López     │ 20:02  │ Combo Familiar  │ $5800 │🔵 En Prep. │ │
│ │    │ 11-9876-5432    │        │ 1 Fanta 600ml   │       │  💵 Destino│ │
│ │    │                 │        │                 │       │[Ver detalle]│
│ ├──────────────────────────────────────────────────────────────────────┤ │
│ │ 40 │ Carlos Ruiz     │ 19:50  │ 1 Fugazzeta ch. │ $2100 │🟠 A Desp.  │ │
│ │    │ 11-5555-0000    │        │ 6x Pollo        │       │  💳 Pagado │ │
│ │    │                 │        │                 │       │[Ver detalle]│
│ └──────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### 12.3 Detalle de Pedido (Panel lateral o modal)

```
┌──────────────────────────────────────────────────────┐
│  PEDIDO #42                              [X Cerrar]  │
├──────────────────────────────────────────────────────┤
│  👤 Juan Pérez  |  📱 11-1234-5678                   │
│  📦 Delivery    |  📍 Av. Siempre Viva 742           │
│  🕐 Recibido: Hoy 20:15                              │
├──────────────────────────────────────────────────────┤
│  PRODUCTOS                                           │
│  • 1x Pizza Mozzarella Grande         $2.100         │
│  • 2x Empanada Carne Suave            $  700         │
│  • 1x Coca-Cola 1.5L                  $  400         │
│  ─────────────────────────────────────────           │
│  TOTAL                                $3.200         │
├──────────────────────────────────────────────────────┤
│  💳 Pago: MercadoPago — PAGADO ✅                    │
├──────────────────────────────────────────────────────┤
│  HISTORIAL                                           │
│  ✅ 20:15  Pedido recibido                           │
│  ✅ 20:16  Link de pago enviado                      │
│  ✅ 20:18  Pago confirmado                           │
│  🟡 20:18  Pendiente de preparación (actual)         │
├──────────────────────────────────────────────────────┤
│  📝 Notas internas:                                  │
│  ┌────────────────────────────────────────────────┐  │
│  │ Sin sal en las empanadas                       │  │
│  └────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────┤
│  [ ➡ Iniciar Preparación ]    [ ✖ Cancelar pedido ] │
└──────────────────────────────────────────────────────┘
```

---

### 12.4 ABM de Menú — Vista de Pizzas

```
┌──────────────────────────────────────────────────────────────────────────┐
│  🍕 Panel Pizzería   [Pedidos] [Menú] [Reportes] [Config]     👤 Admin ▼ │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  MENÚ  > Pizzas                                  [+ Nueva Pizza]         │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ Nombre        │ Precio Grande │ Precio Chica │ Disponible │ Acciones │ │
│ ├──────────────────────────────────────────────────────────────────────┤ │
│ │ Mozzarella    │    $2.100     │    $1.500    │    ✅ Sí   │ ✏️  🗑️  │ │
│ │ Fugazzeta     │    $2.400     │    $1.700    │    ✅ Sí   │ ✏️  🗑️  │ │
│ │ Napolitana    │    $2.300     │    $1.650    │    ❌ No   │ ✏️  🗑️  │ │
│ │ Cuatro Quesos │    $2.600     │    $1.900    │    ✅ Sí   │ ✏️  🗑️  │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ⚙️ Recargo mitad y mitad: $300     [Editar]                            │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### 12.5 Reportes — Vista de Ventas del Día

```
┌──────────────────────────────────────────────────────────────────────────┐
│  🍕 Panel Pizzería   [Pedidos] [Menú] [Reportes] [Config]     👤 Admin ▼ │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  REPORTES > Ventas    Período: [Hoy ▼]  [26/03/2026 – 26/03/2026]       │
│                                                                          │
│ ┌────────────────┐  ┌────────────────┐  ┌────────────────┐              │
│ │  Total vendido │  │  Pedidos hoy   │  │  Ticket prom.  │              │
│ │   $48.200      │  │      17        │  │    $2.835      │              │
│ └────────────────┘  └────────────────┘  └────────────────┘              │
│                                                                          │
│  MÉTODOS DE PAGO                                                         │
│  ████████████████ MercadoPago   $31.400  (65%)                          │
│  ████████         Efectivo      $12.800  (26%)                          │
│  ████             Transferencia $ 4.000  ( 9%)                          │
│                                                                          │
│  PRODUCTOS MÁS VENDIDOS (unidades)                                       │
│  1. Pizza Mozzarella Grande  ───────────────────  12 uds                 │
│  2. Empanada Carne Suave     ──────────────────   48 uds                 │
│  3. Combo Familiar           ──────────────       7 uds                  │
│  4. Coca-Cola 1.5L           ─────────────        9 uds                  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### 12.6 Inventario — Lista de Productos

```
┌──────────────────────────────────────────────────────────────────────────┐
│  🍕 Panel Pizzería   [Pedidos] [Menú] [Reportes] [Config]     👤 Admin ▼ │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  MENÚ  > Inventario / Lista de Productos         [+ Nuevo Producto]      │
│                                                                          │
│  Buscar: [________________]   Categoría: [Todas ▼]   Estado: [Todos ▼]  │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ Código     │ Nombre corto   │ Nombre completo         │ Cat.  │ Estado│ │
│ ├──────────────────────────────────────────────────────────────────────┤ │
│ │ PIZ-MOZ    │ Mozza          │ Pizza Mozzarella        │ Pizza │ ✅ Sí │ │
│ │            │ Salsa de tomate, mozzarella, orégano                    │ │
│ │            │                                               │ ✏️  🚫 │ │
│ ├──────────────────────────────────────────────────────────────────────┤ │
│ │ PIZ-FUG    │ Fugazzeta      │ Pizza Fugazzeta         │ Pizza │ ✅ Sí │ │
│ │            │ Cebolla, mozzarella, aceitunas negras                   │ │
│ │            │                                               │ ✏️  🚫 │ │
│ ├──────────────────────────────────────────────────────────────────────┤ │
│ │ EMP-CAR    │ Carne suave    │ Empanada de Carne Suave │ Empa. │ ✅ Sí │ │
│ │            │ Carne picada, cebolla, pimiento, huevo                  │ │
│ │            │                                               │ ✏️  🚫 │ │
│ ├──────────────────────────────────────────────────────────────────────┤ │
│ │ BEB-COCA15 │ Coca 1.5L      │ Coca-Cola 1.5 litros    │ Beb.  │ ✅ Sí │ │
│ │            │ Botella de Coca-Cola 1.5L                               │ │
│ │            │                                               │ ✏️  🚫 │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  Mostrando 4 de 12 productos    [← Anterior]  Página 1/3  [Siguiente →] │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Modal — Nuevo Producto / Editar Producto:**

```
┌──────────────────────────────────────────────────────┐
│  NUEVO PRODUCTO                          [X Cerrar]  │
├──────────────────────────────────────────────────────┤
│  Código / ID *                                       │
│  ┌────────────────────────────────────────────────┐  │
│  │ PIZ-                                           │  │
│  └────────────────────────────────────────────────┘  │
│  (No editable luego de creado)                       │
│                                                      │
│  Categoría *          [Pizza        ▼]               │
│                                                      │
│  Nombre corto *  (máx. 30 caracteres)                │
│  ┌────────────────────────────────────────────────┐  │
│  │                                                │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  Nombre completo *                                   │
│  ┌────────────────────────────────────────────────┐  │
│  │                                                │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  Descripción (ingredientes / contenido)              │
│  ┌────────────────────────────────────────────────┐  │
│  │                                                │  │
│  │                                                │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  Disponible:  ● Sí   ○ No                            │
│                                                      │
│       [ Cancelar ]        [ Guardar producto ]       │
└──────────────────────────────────────────────────────┘
```

---

### 12.7 Conversaciones Activas — Pantalla de Derivación Humana

```
┌──────────────────────────────────────────────────────────────────────────┐
│  🍕 Panel Pizzería   [Pedidos] [Chats] [Menú] [Reportes]   👤 Cajero ▼  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  💬 CONVERSACIONES ACTIVAS          🔴 2 esperando operador              │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ Cliente          │ Espera  │ Pedido en curso         │ Estado        │ │
│ ├──────────────────────────────────────────────────────────────────────┤ │
│ │ Juan Pérez       │ 3 min   │ 1x Mozza Gde, 6x Carne  │ 🔴 Esperando │ │
│ │ 11-1234-5678     │         │ Subtotal: $3.900         │ [Atender]    │ │
│ ├──────────────────────────────────────────────────────────────────────┤ │
│ │ Ana Gómez        │ 1 min   │ (sin ítems aún)          │ 🔴 Esperando │ │
│ │ 11-9999-0000     │         │                          │ [Atender]    │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Vista de atención — operador tomó la conversación:**

```
┌──────────────────────────────────────────────────────────────────────┐
│  💬 Chat con Juan Pérez  (11-1234-5678)          [Finalizar atención] │
├───────────────────────────┬──────────────────────────────────────────┤
│  HISTORIAL DEL CHAT       │  PEDIDO EN CURSO                         │
│                           │                                          │
│  [Bot] Hola Juan! ¿Qué    │  • 1x Pizza Mozzarella Grande   $2.100  │
│  vas a pedir hoy?         │  • 6x Empanada Carne Suave      $1.800  │
│                           │  ─────────────────────────────────────  │
│  [Juan] quiero una mozza  │  Subtotal                       $3.900  │
│  grande y 6 empanadas     │                                          │
│  de carne                 │  [+ Agregar producto]                    │
│                           │                                          │
│  [Bot] Anotado. ¿Algo más?│  Entrega: 🚚 Delivery                   │
│                           │  Dirección: Av. Siempre Viva 742         │
│  [Juan] si, hablame con   │  Pago: (pendiente)                       │
│  una persona              │                                          │
│                           │  [ ✅ Confirmar pedido ]                 │
│  [Bot] En un momento      │                                          │
│  te atiende alguien...    ├──────────────────────────────────────────┤
│                           │  DATOS DEL CLIENTE                       │
│  ── Operador conectado ── │  Nombre: Juan Pérez                      │
│                           │  Tel: 11-1234-5678                       │
│  ┌─────────────────────┐  │  Dirección: Av. Siempre Viva 742         │
│  │ Escribir mensaje... │  │  Crédito a favor: $0                     │
│  └─────────────────────┘  │                                          │
│  [Enviar por WhatsApp]    │  [ Devolver al bot ] [ Cerrar sin pedido]│
└───────────────────────────┴──────────────────────────────────────────┘
```

---

### 12.8 Pedido Telefónico — Formulario de Carga Manual

```
┌──────────────────────────────────────────────────────────────────────────┐
│  🍕 Panel Pizzería   [Pedidos] [Chats] [Menú] [Reportes]   👤 Cajero ▼  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📞 NUEVO PEDIDO TELEFÓNICO                                              │
│                                                                          │
│  ── PASO 1: CLIENTE ────────────────────────────────────────────────     │
│                                                                          │
│  Teléfono *   [_______________________]   [🔍 Buscar]                   │
│                                                                          │
│  ┌─ Cliente encontrado ──────────────────────────────────────────────┐   │
│  │  ✅ Juan Pérez  |  Av. Siempre Viva 742  |  📱 Tiene WhatsApp    │   │
│  │  [Usar estos datos]   [Editar]                                    │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  — o completar manualmente —                                             │
│                                                                          │
│  Nombre *      [_______________________]                                 │
│  Dirección     [_______________________]  (dejar vacío si retira)        │
│  ¿Tiene WhatsApp?   ● Sí   ○ No                                         │
│                                                                          │
│  ── PASO 2: PRODUCTOS ──────────────────────────────────────────────     │
│                                                                          │
│  [+ Pizza]  [+ Empanadas]  [+ Bebida]  [+ Combo]                        │
│                                                                          │
│  • 1x Pizza Mozzarella Grande ................ $2.100      [🗑]         │
│  • 6x Empanada Carne Suave ................... $1.800      [🗑]         │
│                                                                          │
│  ── PASO 3: ENTREGA ────────────────────────────────────────────────     │
│  ● Delivery   ○ Retiro en local                                          │
│                                                                          │
│  ── PASO 4: PAGO ───────────────────────────────────────────────────     │
│  ○ Efectivo   ○ Transferencia   ○ MercadoPago (enviar link por WhatsApp) │
│                                                                          │
│  ── RESUMEN ────────────────────────────────────────────────────────     │
│  Subtotal: $3.900   Crédito a favor: $0   Total: $3.900                  │
│                                                                          │
│  Notas internas: [________________________________________]              │
│                                                                          │
│          [ Cancelar ]              [ ✅ Confirmar pedido ]               │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### 12.9 Registro de Pizzería — Flujo de Alta del Dueño

**Paso 1 — Crear cuenta:**
```
┌─────────────────────────────────────────────────────┐
│           🍕 Crear tu cuenta                        │
├─────────────────────────────────────────────────────┤
│  Nombre completo  [_____________________________]   │
│  Email            [_____________________________]   │
│  Contraseña       [_____________________________]   │
│  Confirmar pass   [_____________________________]   │
│  Teléfono         [_____________________________]   │
│                                                     │
│            [ Continuar → ]                          │
│                                                     │
│  ¿Ya tenés cuenta?  [Iniciar sesión]                │
└─────────────────────────────────────────────────────┘
```

**Paso 2 — Datos de la pizzería:**
```
┌─────────────────────────────────────────────────────┐
│           🍕 Tu primera pizzería                    │
├─────────────────────────────────────────────────────┤
│  Nombre de la pizzería  [______________________]    │
│  Dirección              [______________________]    │
│  Localidad / Ciudad     [______________________]    │
│  Logo (opcional)        [ Subir imagen ]            │
│                                                     │
│       [ ← Atrás ]     [ Continuar → ]               │
└─────────────────────────────────────────────────────┘
```

**Paso 3 — Conectar WhatsApp:**
```
┌─────────────────────────────────────────────────────┐
│        📱 Conectar tu WhatsApp                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Escaneá este código QR con el teléfono que         │
│  usará como WhatsApp de la pizzería:                │
│                                                     │
│         ┌───────────────────────┐                   │
│         │  ▓▓▓  ░░  ▓▓▓░░▓▓▓  │                   │
│         │  ░  ░ ▓▓▓ ░  ░▓░  ░  │                   │
│         │  ▓▓▓  ░░░ ▓▓▓░▓▓▓▓  │                   │
│         │  (QR code)            │                   │
│         └───────────────────────┘                   │
│                                                     │
│  Estado: ⏳ Esperando escaneo...                    │
│                                                     │
│  ¿Querés agregar otro número después?               │
│  Podés hacerlo desde Configuración.                 │
│                                                     │
│       [ ← Atrás ]    [ Saltar por ahora ]           │
└─────────────────────────────────────────────────────┘
```

**Paso 4 — Listo:**
```
┌─────────────────────────────────────────────────────┐
│           ✅ ¡Todo listo!                           │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Tu pizzería "Pizzería Centro" está configurada.    │
│  WhatsApp conectado: +54 11 1234-5678               │
│                                                     │
│  Próximos pasos sugeridos:                          │
│  □ Agregar productos al menú                        │
│  □ Configurar precios                               │
│  □ Invitar empleados                               │
│                                                     │
│           [ Ir al panel → ]                         │
└─────────────────────────────────────────────────────┘
```

---

### 12.10 Gestión de Números de WhatsApp (por pizzería)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  🍕 Panel Pizzería   [Pedidos] [Chats] [Menú] [Reportes] [Config]  ▼    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  CONFIG  >  WhatsApp                          [+ Agregar número]         │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ Número             │ Nombre / etiqueta │ Estado       │ Acciones     │ │
│ ├──────────────────────────────────────────────────────────────────────┤ │
│ │ +54 11 1234-5678   │ Número principal  │ 🟢 Conectado │ ✏️  ⏸️  🗑️ │ │
│ │ +54 11 9876-0000   │ Número de respaldo│ 🟢 Conectado │ ✏️  ⏸️  🗑️ │ │
│ │ +54 11 5555-1234   │ Zona Norte        │ 🔴 Desconect.│ ✏️  🔁  🗑️ │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ⚠️  El número "Zona Norte" está desconectado. Reconectar para recibir  │
│     mensajes de ese número.                                              │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### 12.11 Gestión de Empleados (por pizzería)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  🍕 Panel Pizzería   [Pedidos] [Chats] [Menú] [Reportes] [Config]  ▼    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  CONFIG  >  Empleados                         [+ Agregar empleado]       │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ Nombre          │ Email                  │ Rol        │ Acciones     │ │
│ ├──────────────────────────────────────────────────────────────────────┤ │
│ │ María González  │ maria@pizzeria.com     │ Cajero     │ ✏️  🗑️      │ │
│ │ Carlos Ruiz     │ carlos@pizzeria.com    │ Cocinero   │ ✏️  🗑️      │ │
│ │ Laura Pérez     │ laura@pizzeria.com     │ Repartidor │ ✏️  🗑️      │ │
│ │ Marcos López    │ marcos@pizzeria.com    │ Admin      │ ✏️  🗑️      │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  Los empleados reciben un email de invitación para crear su contraseña. │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

*Fin de la especificación funcional — versión 1.8*
