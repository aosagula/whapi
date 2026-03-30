/**
 * Página de pedidos manuales / telefónicos.
 */
import FormularioPedidoManual from "@/components/pedidos-manuales/FormularioPedidoManual"

interface Props {
  params: { comercio_id: string }
}

export default function PedidosManualesPage({ params }: Props) {
  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="font-serif text-3xl text-brown mb-1">Pedido telefónico</h1>
        <p className="text-brown-muted text-sm">Registrá un pedido recibido por teléfono.</p>
      </div>

      <div className="bg-white border rounded-2xl p-6 shadow-sm">
        <FormularioPedidoManual comercioId={params.comercio_id} />
      </div>
    </div>
  )
}
