"""Schemas Pydantic para pagos."""
from __future__ import annotations

from pydantic import BaseModel


class PagoLinkResponse(BaseModel):
    """Respuesta con el link de pago MercadoPago."""
    preference_id: str
    init_point: str
    sandbox_init_point: str
