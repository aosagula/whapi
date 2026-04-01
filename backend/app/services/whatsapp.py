"""Lógica de negocio para números de WhatsApp y sesiones WPPConnect."""
from __future__ import annotations

import re
import uuid

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.whatsapp import WhatsappNumber
from app.schemas.whatsapp import WhatsappNumberCreate, WhatsappNumberUpdate


# ── Helpers WPPConnect ────────────────────────────────────────────────────────

def _wpp_base() -> str:
    """
    URL base del servidor WPPConnect.
    Si el host ya incluye protocolo (http/https), se usa directamente.
    Si no, se construye con el puerto configurado.
    """
    host = settings.WPPCONNECT_HOST.rstrip("/")
    if host.startswith("http://") or host.startswith("https://"):
        return host
    return f"http://{host}:{settings.WPPCONNECT_PORT}"


def _session_name_from_phone(phone: str) -> str:
    """Genera un nombre de sesión seguro a partir del número de teléfono."""
    # Elimina caracteres no alfanuméricos
    return "sess_" + re.sub(r"\D", "", phone)


async def _wpp_request(
    method: str,
    path: str,
    json: dict | None = None,
    token: str | None = None,
) -> dict:
    """
    Realiza una petición al servidor WPPConnect.
    Usa el token de sesión como Bearer si está disponible;
    si no, usa el secret key global.
    Retorna el body parseado o lanza HTTPException si WPPConnect no está disponible.
    """
    if not settings.WPPCONNECT_HOST:
        # WPPConnect no configurado — modo sin integración real
        return {}

    base = _wpp_base()

    # Priorizar token de sesión; fallback al secret key global
    bearer = token or settings.WPPCONNECT_SECRET_KEY
    headers: dict[str, str] = {}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"

    url = f"{base}{path}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.request(method, url, json=json, headers=headers)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error de WPPConnect: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo conectar con el servidor de WhatsApp",
        ) from exc


async def _generar_token_wpp(session_name: str) -> str | None:
    """
    Genera un token de sesión WPPConnect.
    URL: POST /api/{session}/{secret}/generate-token
    Retorna el token generado, o None si falla.
    """
    secret = settings.WPPCONNECT_SECRET_KEY or ""
    data = await _wpp_request("POST", f"/api/{session_name}/{secret}/generate-token")
    return data.get("token") or data.get("data", {}).get("token")


async def _iniciar_sesion_wpp(session_name: str) -> str | None:
    """
    Inicia una sesión WPPConnect (genera token y arranca la sesión).
    Retorna el token generado para persistir en el modelo.
    """
    token = await _generar_token_wpp(session_name)
    # Iniciar sesión pasando el token generado como Bearer (quedará en 'scanning' esperando QR)
    await _wpp_request(
        "POST",
        f"/api/{session_name}/start-session",
        json={"webhook": "", "waitQrCode": False},
        token=token,
    )
    return token


async def _obtener_qr_wpp(session_name: str, token: str | None = None) -> str | None:
    """
    Obtiene el QR de una sesión WPPConnect.
    WPPConnect puede devolver la imagen PNG directamente o un JSON con el base64.
    """
    if not settings.WPPCONNECT_HOST:
        return None

    import base64

    base = _wpp_base()
    bearer = token or settings.WPPCONNECT_SECRET_KEY
    headers: dict[str, str] = {}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"

    url = f"{base}/api/{session_name}/qrcode-session"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            if "image" in content_type:
                # Respuesta binaria PNG → convertir a base64 data URI
                return "data:image/png;base64," + base64.b64encode(resp.content).decode()

            # Respuesta JSON
            data = resp.json()
            return data.get("qrcode") or data.get("data")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error de WPPConnect: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo conectar con el servidor de WhatsApp",
        ) from exc


async def _obtener_status_wpp(session_name: str, token: str | None = None) -> str:
    """Consulta el estado de la sesión en WPPConnect."""
    data = await _wpp_request("GET", f"/api/{session_name}/status-session", token=token)
    raw = (data.get("status") or data.get("session", {}).get("status") or "").lower()
    if "connected" in raw or "islogged" in raw:
        return "connected"
    if "scan" in raw or "qr" in raw:
        return "scanning"
    return "disconnected"


async def _cerrar_sesion_wpp(session_name: str, token: str | None = None) -> None:
    """Cierra y desconecta la sesión WPPConnect."""
    await _wpp_request("POST", f"/api/{session_name}/logout-session", token=token)


# ── CRUD WhatsappNumber ───────────────────────────────────────────────────────

async def listar_numeros(
    business_id: uuid.UUID,
    db: AsyncSession,
) -> list[WhatsappNumber]:
    """Lista todos los números (activos e inactivos) del comercio."""
    result = await db.execute(
        select(WhatsappNumber)
        .where(WhatsappNumber.business_id == business_id)
        .order_by(WhatsappNumber.created_at)
    )
    return list(result.scalars().all())


async def agregar_numero(
    business_id: uuid.UUID,
    data: WhatsappNumberCreate,
    db: AsyncSession,
) -> WhatsappNumber:
    """
    Agrega un número de WhatsApp al comercio e inicia la sesión WPPConnect.
    El número queda en estado 'scanning' esperando que el usuario escanee el QR.
    """
    # Verificar que el número no esté ya registrado en este comercio
    existing = await db.execute(
        select(WhatsappNumber).where(
            WhatsappNumber.business_id == business_id,
            WhatsappNumber.phone_number == data.phone_number,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El número ya está registrado en este comercio",
        )

    session_name = _session_name_from_phone(data.phone_number)

    numero = WhatsappNumber(
        business_id=business_id,
        phone_number=data.phone_number,
        label=data.label,
        session_name=session_name,
        status="scanning",
        is_active=True,
    )
    db.add(numero)
    await db.flush()

    # Iniciar sesión en WPPConnect (si está configurado) y persistir token
    if settings.WPPCONNECT_HOST:
        token = await _iniciar_sesion_wpp(session_name)
        if token:
            numero.wpp_token = token

    await db.commit()
    await db.refresh(numero)
    return numero


async def obtener_qr(
    business_id: uuid.UUID,
    numero_id: uuid.UUID,
    db: AsyncSession,
) -> tuple[WhatsappNumber, str | None]:
    """
    Obtiene el QR de una sesión y actualiza el estado del número.
    Retorna (numero, qr_base64).
    """
    numero = await _get_numero_o_404(business_id, numero_id, db)
    qr = None

    if settings.WPPCONNECT_HOST and numero.session_name:
        status_wpp = await _obtener_status_wpp(numero.session_name, token=numero.wpp_token)
        numero.status = status_wpp  # type: ignore[assignment]

        if status_wpp == "scanning":
            qr = await _obtener_qr_wpp(numero.session_name, token=numero.wpp_token)

        await db.commit()
        await db.refresh(numero)

    return numero, qr


async def reconectar_numero(
    business_id: uuid.UUID,
    numero_id: uuid.UUID,
    db: AsyncSession,
) -> tuple[WhatsappNumber, str | None]:
    """
    Reconecta un número desconectado: reinicia la sesión WPPConnect
    y devuelve el nuevo QR para escanear.
    """
    numero = await _get_numero_o_404(business_id, numero_id, db)
    qr = None

    numero.status = "scanning"  # type: ignore[assignment]

    if settings.WPPCONNECT_HOST and numero.session_name:
        token = await _iniciar_sesion_wpp(numero.session_name)
        if token:
            numero.wpp_token = token
        qr = await _obtener_qr_wpp(numero.session_name, token=numero.wpp_token)

    await db.commit()
    await db.refresh(numero)
    return numero, qr


async def editar_numero(
    business_id: uuid.UUID,
    numero_id: uuid.UUID,
    data: WhatsappNumberUpdate,
    db: AsyncSession,
) -> WhatsappNumber:
    """Edita la etiqueta o el estado activo de un número."""
    numero = await _get_numero_o_404(business_id, numero_id, db)

    if data.label is not None:
        numero.label = data.label
    if data.is_active is not None:
        numero.is_active = data.is_active

    await db.commit()
    await db.refresh(numero)
    return numero


async def eliminar_numero(
    business_id: uuid.UUID,
    numero_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """
    Elimina un número: cierra la sesión WPPConnect y lo marca como inactivo.
    Las conversaciones históricas se conservan.
    """
    numero = await _get_numero_o_404(business_id, numero_id, db)

    if settings.WPPCONNECT_HOST and numero.session_name:
        # Intentar cerrar sesión; si falla no bloqueamos la eliminación
        try:
            await _cerrar_sesion_wpp(numero.session_name, token=numero.wpp_token)
        except HTTPException:
            pass

    numero.is_active = False
    numero.status = "disconnected"  # type: ignore[assignment]
    await db.commit()


# ── Helper interno ────────────────────────────────────────────────────────────

async def _get_numero_o_404(
    business_id: uuid.UUID,
    numero_id: uuid.UUID,
    db: AsyncSession,
) -> WhatsappNumber:
    result = await db.execute(
        select(WhatsappNumber).where(
            WhatsappNumber.id == numero_id,
            WhatsappNumber.business_id == business_id,
        )
    )
    numero = result.scalar_one_or_none()
    if numero is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Número de WhatsApp no encontrado",
        )
    return numero
