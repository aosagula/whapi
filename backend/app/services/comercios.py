"""Lógica de negocio para comercios y empleados."""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Business, User, UserBusiness
from app.schemas.comercio import (
    ComercioCreate,
    ComercioUpdate,
    EmpleadoAsociarRequest,
    EmpleadoCambiarRolRequest,
)


# ── Comercios ──────────────────────────────────────────────────────────────────

async def crear_comercio(
    data: ComercioCreate,
    owner: User,
    db: AsyncSession,
) -> Business:
    """
    Crea un comercio y asocia automáticamente al dueño con rol 'owner'.
    Regla de negocio: al crear un comercio, el dueño queda asociado automáticamente.
    """
    business = Business(
        owner_id=owner.id,
        name=data.name,
        address=data.address,
        logo_url=data.logo_url,
        half_half_surcharge=data.half_half_surcharge,
    )
    db.add(business)
    await db.flush()  # obtener el ID antes del commit

    # Auto-asociar al dueño con rol owner
    membresia = UserBusiness(
        user_id=owner.id,
        business_id=business.id,
        role="owner",
    )
    db.add(membresia)
    await db.commit()
    await db.refresh(business)
    return business


async def editar_comercio(
    business: Business,
    data: ComercioUpdate,
    db: AsyncSession,
) -> Business:
    """Actualiza los campos editables del comercio."""
    if data.name is not None:
        business.name = data.name
    if data.address is not None:
        business.address = data.address
    if data.logo_url is not None:
        business.logo_url = data.logo_url
    if data.half_half_surcharge is not None:
        business.half_half_surcharge = data.half_half_surcharge
    await db.commit()
    await db.refresh(business)
    return business


# ── Empleados ──────────────────────────────────────────────────────────────────

async def listar_empleados(
    business_id: uuid.UUID,
    db: AsyncSession,
) -> list[tuple[User, UserBusiness]]:
    """Retorna todos los miembros activos del comercio con su membresía."""
    result = await db.execute(
        select(User, UserBusiness)
        .join(UserBusiness, UserBusiness.user_id == User.id)
        .where(
            UserBusiness.business_id == business_id,
            UserBusiness.is_active == True,  # noqa: E712
        )
        .order_by(User.name)
    )
    return result.all()


async def asociar_empleado(
    business_id: uuid.UUID,
    data: EmpleadoAsociarRequest,
    db: AsyncSession,
) -> tuple[User, UserBusiness]:
    """
    Asocia un usuario existente al comercio con el rol indicado.
    Lanza 404 si el email no existe. Lanza 409 si ya es miembro activo.
    """
    # Buscar usuario por email
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe ningún usuario con ese email",
        )

    # Verificar si ya es miembro activo
    result = await db.execute(
        select(UserBusiness).where(
            UserBusiness.user_id == user.id,
            UserBusiness.business_id == business_id,
        )
    )
    existente = result.scalar_one_or_none()

    if existente is not None:
        if existente.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El usuario ya es miembro de este comercio",
            )
        # Reactivar membresía anterior
        existente.is_active = True
        existente.role = data.role
        await db.commit()
        await db.refresh(existente)
        return user, existente

    membresia = UserBusiness(
        user_id=user.id,
        business_id=business_id,
        role=data.role,
    )
    db.add(membresia)
    await db.commit()
    await db.refresh(membresia)
    return user, membresia


async def cambiar_rol_empleado(
    business_id: uuid.UUID,
    target_user_id: uuid.UUID,
    data: EmpleadoCambiarRolRequest,
    db: AsyncSession,
) -> tuple[User, UserBusiness]:
    """Cambia el rol de un miembro activo. No permite cambiar el rol del owner."""
    result = await db.execute(
        select(User, UserBusiness)
        .join(UserBusiness, UserBusiness.user_id == User.id)
        .where(
            UserBusiness.user_id == target_user_id,
            UserBusiness.business_id == business_id,
            UserBusiness.is_active == True,  # noqa: E712
        )
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    user, membresia = row
    if membresia.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede cambiar el rol del owner",
        )

    membresia.role = data.role
    await db.commit()
    await db.refresh(membresia)
    return user, membresia


async def dar_de_baja_empleado(
    business_id: uuid.UUID,
    target_user_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """
    Desasocia un empleado del comercio (soft delete en la membresía).
    No permite dar de baja al owner.
    """
    result = await db.execute(
        select(UserBusiness).where(
            UserBusiness.user_id == target_user_id,
            UserBusiness.business_id == business_id,
            UserBusiness.is_active == True,  # noqa: E712
        )
    )
    membresia = result.scalar_one_or_none()
    if membresia is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    if membresia.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede dar de baja al owner del comercio",
        )

    membresia.is_active = False
    await db.commit()
