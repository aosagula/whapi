"""Endpoints de comercios del usuario autenticado."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.account import Business, User, UserBusiness
from app.schemas.comercio import ComercioResponse, MisComerciosResponse

router = APIRouter(prefix="/comercios", tags=["comercios"])


@router.get("/mis-comercios", response_model=MisComerciosResponse)
async def mis_comercios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MisComerciosResponse:
    """Retorna la lista de comercios a los que pertenece el usuario autenticado."""
    result = await db.execute(
        select(Business, UserBusiness.role)
        .join(UserBusiness, UserBusiness.business_id == Business.id)
        .where(
            UserBusiness.user_id == current_user.id,
            UserBusiness.is_active == True,  # noqa: E712
            Business.is_active == True,  # noqa: E712
        )
        .order_by(Business.name)
    )
    rows = result.all()

    comercios = [
        ComercioResponse(
            id=business.id,
            name=business.name,
            address=business.address,
            logo_url=business.logo_url,
            is_active=business.is_active,
            role=role,
        )
        for business, role in rows
    ]
    return MisComerciosResponse(comercios=comercios)
