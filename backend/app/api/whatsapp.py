"""Endpoints de gestión de números de WhatsApp por comercio."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import get_membresia, get_membresia_gestion
from app.models.account import Business, UserBusiness
from app.schemas.whatsapp import (
    WhatsappNumberCreate,
    WhatsappNumberResponse,
    WhatsappNumberUpdate,
    WhatsappQRResponse,
)
from app.services.whatsapp import (
    agregar_numero,
    editar_numero,
    eliminar_numero,
    listar_numeros,
    obtener_qr,
    reconectar_numero,
)

router = APIRouter(
    prefix="/comercios/{comercio_id}/whatsapp",
    tags=["whatsapp"],
)


def _to_response(numero) -> WhatsappNumberResponse:
    return WhatsappNumberResponse(
        id=numero.id,
        business_id=numero.business_id,
        phone_number=numero.phone_number,
        label=numero.label if hasattr(numero, "label") else numero.session_name,
        session_name=numero.session_name,
        status=numero.status,
        is_active=numero.is_active,
        created_at=numero.created_at,
        updated_at=numero.updated_at,
    )


@router.get("", response_model=list[WhatsappNumberResponse])
async def listar(
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> list[WhatsappNumberResponse]:
    """Lista los números de WhatsApp del comercio. Requiere owner o admin."""
    business, _ = ctx
    numeros = await listar_numeros(business.id, db)
    return [_to_response(n) for n in numeros]


@router.post("", response_model=WhatsappNumberResponse, status_code=status.HTTP_201_CREATED)
async def agregar(
    data: WhatsappNumberCreate,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> WhatsappNumberResponse:
    """Agrega un número e inicia la sesión WPPConnect. Requiere owner o admin."""
    business, _ = ctx
    numero = await agregar_numero(business.id, data, db)
    return _to_response(numero)


@router.get("/{numero_id}/qr", response_model=WhatsappQRResponse)
async def qr(
    numero_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> WhatsappQRResponse:
    """Obtiene el QR de escaneo de una sesión. Requiere owner o admin."""
    business, _ = ctx
    numero, qr_code = await obtener_qr(business.id, numero_id, db)
    return WhatsappQRResponse(
        session_name=numero.session_name or "",
        qr_code=qr_code,
        status=numero.status,
    )


@router.post("/{numero_id}/reconectar", response_model=WhatsappQRResponse)
async def reconectar(
    numero_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> WhatsappQRResponse:
    """Reinicia la sesión WPPConnect y devuelve nuevo QR. Requiere owner o admin."""
    business, _ = ctx
    numero, qr_code = await reconectar_numero(business.id, numero_id, db)
    return WhatsappQRResponse(
        session_name=numero.session_name or "",
        qr_code=qr_code,
        status=numero.status,
    )


@router.patch("/{numero_id}", response_model=WhatsappNumberResponse)
async def editar(
    numero_id: uuid.UUID,
    data: WhatsappNumberUpdate,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> WhatsappNumberResponse:
    """Edita la etiqueta o estado activo de un número. Requiere owner o admin."""
    business, _ = ctx
    numero = await editar_numero(business.id, numero_id, data, db)
    return _to_response(numero)


@router.delete("/{numero_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar(
    numero_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Elimina un número y cierra su sesión WPPConnect. Requiere owner o admin."""
    business, _ = ctx
    await eliminar_numero(business.id, numero_id, db)
