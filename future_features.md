# Funcionalidades Futuras

Este archivo recopila pedidos de funcionalidades solicitadas para implementación futura.
Cada entrada indica la funcionalidad, contexto y fecha del pedido.

---

<!-- Formato de cada entrada:
## [Título breve]
- **Fecha**: YYYY-MM-DD
- **Descripción**: ...
- **Contexto / motivación**: ...
-->

## Mapa de pedidos para optimizar el reparto

- **Fecha**: 2026-03-31
- **Descripción**: Vista de mapa (ej. Leaflet o Google Maps) que muestre la ubicación geográfica de los pedidos activos, para ayudar al repartidor o encargado a planificar y optimizar las rutas de entrega.
- **Contexto / motivación**: Facilitar la distribución eficiente de pedidos entre repartidores y reducir tiempos de entrega.

## Asignación de pedidos a repartidores

- **Fecha**: 2026-03-31
- **Descripción**: Un pedido en estado `en_camino` puede estar asignado a un repartidor específico. Los propios repartidores se auto-asignan los pedidos sin necesidad de un rol coordinador. El pedido muestra el nombre del repartidor responsable.
- **Contexto / motivación**: El comercio puede tener varios repartidores activos simultáneamente. La auto-asignación evita cuellos de botella y no requiere un rol adicional de coordinación.
- **Implicancias técnicas**:
  - Agregar FK `repartidor_id` (nullable) en el modelo `Pedido` apuntando a `Empleado`.
  - El rol `repartidor` ya existe; solo se necesita exponer la acción de auto-asignación en la UI.
  - Integra naturalmente con el mapa de pedidos: cada pin puede mostrar a qué repartidor está asignado.

## Pedido de mostrador / sin teléfono

- **Fecha**: 2026-03-31
- **Descripción**: El formulario de carga manual debe soportar pedidos que no requieren teléfono del cliente. Dos casos: (1) pedido de mostrador (cliente presente físicamente), (2) cliente llama por teléfono pero no quiere dejar su número. En ambos casos se puede continuar con el armado del pedido sin identificar al cliente.
- **Contexto / motivación**: El flujo actual obliga a ingresar un número de teléfono como primer paso, lo que no aplica para ventas en mostrador ni para clientes que prefieren el anonimato.
- **Implicancias técnicas**:
  - El origen `mostrador` se agrega como nuevo valor al campo `origen` del pedido (actualmente `whatsapp` / `telefonico` / `operador`).
  - El `cliente_id` pasa a ser nullable para pedidos sin identificación.
  - El paso 1 del formulario ofrece tres opciones: "Buscar por teléfono", "Cliente de mostrador" (sin datos), "Continuar sin teléfono" (llamada anónima).
  - Los reportes deben agrupar correctamente pedidos sin cliente asociado.
