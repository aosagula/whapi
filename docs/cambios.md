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
