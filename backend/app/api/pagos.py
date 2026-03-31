"""Endpoint para generar link de pago MercadoPago desde el panel."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import get_membresia_gestion
from app.models.account import Business, UserBusiness
from app.models.customer import Customer
from app.models.order import Order
from app.schemas.pagos import PagoLinkResponse
from app.services.mercadopago import crear_preferencia
from app.services.notificaciones import notificar_link_pago
from fastapi import HTTPException, status

router = APIRouter(prefix="/comercios/{comercio_id}/pedidos", tags=["pagos"])


@router.post("/{pedido_id}/pago-link", response_model=PagoLinkResponse)
async def generar_link_pago(
    pedido_id: uuid.UUID,
    request: Request,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> PagoLinkResponse:
    """
    Genera un link de pago MercadoPago para el pedido.
    Requiere owner o admin. Solo disponible cuando el pedido tiene pago pendiente.
    """
    business, _ = ctx

    # Obtener pedido con cliente
    result = await db.execute(
        select(Order)
        .where(Order.id == pedido_id, Order.business_id == business.id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")

    if order.payment_status not in ("pending_payment",):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pedido no tiene pago pendiente",
        )

    # Obtener cliente
    cust_result = await db.execute(
        select(Customer).where(Customer.id == order.customer_id)
    )
    customer = cust_result.scalar_one_or_none()

    # URL de notificación del webhook de MP (base URL del servidor)
    base_url = str(request.base_url).rstrip("/")
    notification_url = f"{base_url}/webhooks/mercadopago"

    pref = await crear_preferencia(
        order_id=order.id,
        order_number=order.order_number,
        total_amount=float(order.total_amount),
        customer_phone=customer.phone if customer else "",
        business_name=business.name,
        notification_url=notification_url,
    )

    # Notificar al cliente con el link
    if customer:
        await notificar_link_pago(
            business_id=business.id,
            order_number=order.order_number,
            link=pref["init_point"],
            customer_phone=customer.phone,
            db=db,
        )

    return PagoLinkResponse(
        preference_id=pref["preference_id"],
        init_point=pref["init_point"],
        sandbox_init_point=pref.get("sandbox_init_point", pref["init_point"]),
    )
