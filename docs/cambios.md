[x] 1. Agregar en la configuracion del telefono la posibilidad de hacer un re-scan del QR para volver a vincularlo.
[x] 1.b. deberia ademas poder desconectar un telefono.
[x] 1.c El mensaje de alerta al desconectar el telefono deberia ser un modal mas bonito respetando los estilos de la aplicacion. 
[x] 1.d Al conectar aparece un modal indicando que hay que escanear el codigo QR, pero nunca aparece la imagen y luego el telefono aparece como conectado pero no es asi.
[x] 1.e permitir insertar un numero de telefono que fue eliminado
[x] 2. Chats con whatsapp en Conversaciones
[x] 2.a Guardar las conversaciones de entrada y salida por cada telefono que nos envia un mensaje, si el telefono es conocido guardar en la conversacion el nombre del cliente.
[x] 2.b Guardar el estado de la conversacion (en curso, finalizada, etc.)
[x] 2.c Mostrar el estado de la conversacion en la lista de conversaciones
[x] 2.d Mostrar el nombre del cliente en la lista de conversaciones
[x] 2.e Mostrar el numero de telefono en la lista de conversaciones
[x] 2.f Resolver correctamente nombre y telefono del remitente cuando WPPConnect entregue identificadores @lid. Si el contacto esta agendado en el telefono vinculado usar ese nombre para mostrar en Clientes y Conversaciones; si no, usar el nombre del perfil del mensaje. Conservar tambien el nombre del perfil para el agente de AI y guardar el payload completo recibido.
[x] 3. Asegurar que cuando un telefono se da de baja previamente se cierra la session con el wppconnect. Un telefono activo solo puede tener una sesion abierta en wppconnect, el resto se deben cerrar. Utilizar la api de wppconnect para cerrar las sesiones.
[x] 4. Agregar en Ajustes una opcion de Asistente, donde se le pueda indicar nombre, un system prompt maestro y un system prompt por defecto.
[ ] 5. Agregar agentes para responder a mensajes de clientes, tener presente que primero debe determinar que quiere preguntar y ofrecer las opciones disponibles de los productos. debe asegurarse si el cliente va a pasar a buscarlo por el local o hay que enviarselo, en ese caso debe estar clara la direccion de entrega, calle, numero de puerta, entre calles. Tambien tiene que asegurarse que el cliente sabe el costo total de la compra y como lo va a pagar si es en efectivo, mercado pago o si es por transferencia.
El el caso de efectivo el agente solo marca esa opcion. En el caso de transferencia se le envian los datos por whatsapp con el importe a abonar y se queda a la espera del comprobante, tambien se marca esa opcion. En el caso de mercado pago se debe preparar un link de mercado pago para que el cliente pueda abonar. para este caso utilizaria gemma de google localmente en un docker porque el razonamiento que se necesita es limitado a las opciones de la pizzeria.
Plan propuesto para el punto 5:
[x] 5.a. Definir arquitectura del agente.
- Usar Gemma local en Docker como motor LLM.
- Reemplazar n8n por una orquestación en código dentro del backend, preferentemente con LangGraph/LangChain.
- Dejar al backend como fuente de verdad para clientes, sesiones, catálogo, pedidos, pagos y mensajes.

[x] 5.b. Configurar el runtime del modelo local.
- Agregar servicio Docker para Gemma con endpoint HTTP interno.
- Definir variables de entorno para URL del modelo, modelo activo, timeout y límites de contexto.
- Agregar healthcheck y logging para saber si el modelo está disponible.

[x] 5.c. Definir la capa de orquestación.
- Opción recomendada: LangGraph para modelar estados, transiciones y tools del agente.
- Opción alternativa más simple: servicio propio en Python con máquina de estados explícita, sin LangChain.
- No usar n8n para el flujo principal del chatbot; toda la lógica de decisión debe vivir en código versionado dentro del repo.

[x] 5.d. Crear un endpoint backend de inferencia controlada.
- Exponer un servicio interno que reciba contexto estructurado y devuelva intención, datos extraídos y respuesta sugerida.
- No delegar al LLM la escritura directa en base; el LLM solo propone.
- Validar salida con esquema estricto: intención, mensajes, delivery_type, dirección, items, total, payment_method, missing_fields, requiere_humano.

[ ] 5.e. Construir el contexto del agente por comercio.
- Combinar nombre del asistente, system prompt maestro y system prompt por defecto cargados en Ajustes.
- Inyectar catálogo disponible, combos, precios, recargo mitad y mitad, datos del cliente conocido y pedido en curso.
- Incluir reglas de negocio explícitas: no inventar productos, no confirmar si faltan datos, no avanzar si no hay total o medio de pago.

[ ] 5.f. Modelar el estado conversacional mínimo.
- Reutilizar `conversation_sessions` y `orders` existentes.
- Agregar en sesión o pedido un bloque JSON de estado del agente para campos pendientes, último resumen, intención actual y etapa.
- Etapas mínimas: consulta general, armado del pedido, validación de entrega, validación de pago, pendiente de comprobante, confirmado, derivado.

[ ] 5.g. Implementar flujo de entrada de mensajes.
- Webhook WPPConnect guarda mensaje entrante como hoy.
- El backend detecta sesión activa, arma el contexto y ejecuta el grafo o la máquina de estados.
- El agente debe primero clasificar si el cliente consulta catálogo, precio, estado de pedido o quiere comprar.
- Si quiere comprar, debe guiar el flujo sin saltear validaciones.

[ ] 5.h. Implementar armado de pedido con validaciones.
- Resolver productos y combos solo contra el catálogo real.
- Permitir aclaraciones iterativas: tamaño, cantidad, gustos, bebidas, combos.
- Mantener pedido borrador `in_progress` y actualizarlo a medida que el cliente confirma ítems.
- Recalcular total en cada cambio desde backend, no desde el LLM.

[ ] 5.i. Implementar validación de entrega.
- Preguntar si retira en local o si es delivery.
- Si es delivery, exigir calle, número y entre calles antes de avanzar.
- Si falta algún dato, dejarlo explícito en `missing_fields` y pedir solo eso.

[ ] 5.j. Implementar validación de cierre comercial.
- Antes de pasar a pago, el agente debe enviar resumen del pedido con total final.
- Debe confirmar que el cliente entendió qué compra, cuánto paga y cómo lo paga.
- Solo después marcar pedido listo para pago o confirmación final.

[ ] 5.k. Implementar flujo por medio de pago.
- Efectivo: registrar método `cash` y avanzar a confirmación operativa.
- Transferencia: registrar método `transfer`, enviar datos bancarios por WhatsApp con el importe exacto y pasar a estado pendiente de comprobante.
- MercadoPago: generar link real desde backend, guardar `preference_id` y enviar el link al cliente.

[ ] 5.l. Implementar recepción de comprobantes y pagos.
- Si el cliente responde con texto o imagen luego de transferencia, marcar la conversación como pendiente de revisión humana o cajero.
- Si llega webhook de MercadoPago aprobado, actualizar pedido y notificar automáticamente.
- Evitar que el agente vuelva a pedir pago si el pedido ya quedó pagado o en verificación.

[ ] 5.m. Implementar reglas de derivación a humano.
- Derivar si el agente detecta ambigüedad persistente, reclamo, incidente, falta de confianza o pedido fuera de catálogo.
- Derivar también si el cliente envía comprobantes, audios no soportados o pide hablar con una persona.
- Registrar motivo de derivación para mostrarlo en Conversaciones.

[ ] 5.n. Persistencia y auditoría.
- Guardar cada respuesta del agente como mensaje outbound.
- Guardar también decisión estructurada del turno en un JSON auditable para debugging.
- Registrar qué prompt y qué versión del flujo/grafo/modelo se usó en cada respuesta.

[ ] 5.o. Configuración operativa por comercio.
- Extender Ajustes del Asistente con datos bancarios para transferencia y textos auxiliares de pago.
- Permitir activar/desactivar agente por número de WhatsApp o por comercio.
- Permitir fallback a atención humana si el modelo local no responde.

[ ] 5.p. Testing y validación.
- Tests backend para: consulta de catálogo, armado de pedido, delivery con dirección incompleta, cash, transferencia, MercadoPago, derivación y reanudación.
- Fixtures de conversaciones reales para validar extracción de intención y campos.
- Smoke test end-to-end con webhook entrante → agente → pedido borrador → respuesta WhatsApp.

[ ] 5.q. Despliegue incremental.
- Fase 1: agente responde consultas de catálogo y precios, sin crear pedidos.
- Fase 2: agente crea y actualiza pedidos borrador.
- Fase 3: agente cierra pago cash/transfer/MercadoPago y deriva casos complejos.
- No activar para todos los comercios hasta validar métricas básicas: tasa de derivación, pedidos confirmados, errores de catálogo y tiempos de respuesta.
