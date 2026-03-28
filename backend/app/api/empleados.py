"""Endpoints de gestión de empleados dentro de un comercio."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import get_membresia, get_membresia_gestion
from app.models.account import Business, UserBusiness
from app.schemas.comercio import (
    EmpleadoAsociarRequest,
    EmpleadoCambiarRolRequest,
    EmpleadoResponse,
)
from app.services.comercios import (
    asociar_empleado,
    cambiar_rol_empleado,
    dar_de_baja_empleado,
    listar_empleados,
)

router = APIRouter(prefix="/comercios/{comercio_id}/empleados", tags=["empleados"])


def _to_emp_response(user, membresia: UserBusiness) -> EmpleadoResponse:
    return EmpleadoResponse(
        user_id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        role=membresia.role,
        is_active=membresia.is_active,
        joined_at=membresia.created_at,
    )


@router.get("", response_model=list[EmpleadoResponse])
async def listar(
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> list[EmpleadoResponse]:
    """Lista todos los miembros activos del comercio."""
    business, _ = ctx
    rows = await listar_empleados(business.id, db)
    return [_to_emp_response(u, m) for u, m in rows]


@router.post("", response_model=EmpleadoResponse, status_code=status.HTTP_201_CREATED)
async def asociar(
    data: EmpleadoAsociarRequest,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> EmpleadoResponse:
    """Asocia un usuario existente al comercio (requiere owner o admin)."""
    business, _ = ctx
    user, membresia = await asociar_empleado(business.id, data, db)
    return _to_emp_response(user, membresia)


@router.patch("/{target_user_id}", response_model=EmpleadoResponse)
async def cambiar_rol(
    target_user_id: uuid.UUID,
    data: EmpleadoCambiarRolRequest,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> EmpleadoResponse:
    """Cambia el rol de un empleado (requiere owner o admin)."""
    business, _ = ctx
    user, membresia = await cambiar_rol_empleado(business.id, target_user_id, data, db)
    return _to_emp_response(user, membresia)


@router.delete("/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dar_de_baja(
    target_user_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Da de baja a un empleado del comercio (requiere owner o admin)."""
    business, _ = ctx
    await dar_de_baja_empleado(business.id, target_user_id, db)
