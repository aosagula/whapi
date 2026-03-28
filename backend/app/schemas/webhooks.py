from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# WPPConnect — mensaje entrante
# ---------------------------------------------------------------------------

class WPPConnectMessageId(BaseModel):
    """Identificador de mensaje de WPPConnect."""

    id: str
    remote: str | None = None
    fromMe: bool = False


class WPPConnectMessagePayload(BaseModel):
    """
    Payload que WPPConnect envía al webhook cuando llega un mensaje.
    El campo 'session' identifica la sesión (→ pizzeria_id).
    """

    event: str                                   # "onmessage"
    session: str                                 # session_name en nuestra DB
    type: str | None = None                      # "chat", "image", "document", …
    body: str | None = None                      # texto del mensaje
    sender_phone: str | None = Field(None, alias="from")   # número del remitente
    to: str | None = None                        # nuestro número destino
    is_group: bool = Field(False, alias="isGroup")
    message_id: WPPConnectMessageId | None = Field(None, alias="id")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# WPPConnect — cambio de estado de sesión
# ---------------------------------------------------------------------------

class WPPConnectStatusPayload(BaseModel):
    """
    Payload de cambio de estado de sesión WPPConnect.
    state: 'CONNECTED' | 'DISCONNECTED' | 'UNPAIRED' | 'qrReadSuccess' | …
    """

    session: str
    state: str


# ---------------------------------------------------------------------------
# MercadoPago — notificación de pago
# ---------------------------------------------------------------------------

class MercadoPagoData(BaseModel):
    id: str


class MercadoPagoWebhookPayload(BaseModel):
    """
    Payload de notificación de MercadoPago (IPN / Webhooks v2).
    action: 'payment.created' | 'payment.updated'
    """

    action: str
    data: MercadoPagoData
    live_mode: bool = True
