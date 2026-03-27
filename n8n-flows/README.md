# Flujos de n8n

Los flujos se implementan en la Fase 15. Cada archivo JSON es importable directamente desde la UI de n8n.

| Archivo | Descripción |
|---------|-------------|
| `chatbot-principal.json` | Flujo principal: recibe webhooks de WPPConnect, invoca el LLM y gestiona el estado de la conversación |
| `notificaciones.json` | Envío de notificaciones al cliente ante cambios de estado del pedido |
| `inactividad-timer.json` | Cierre de sesión por inactividad de 10 minutos con consulta previa al cliente |
