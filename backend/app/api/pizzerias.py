from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentAccount, DBSession, OwnerOrAdminRequired, OwnerRequired
from app.models.account import Pizzeria
from app.models.catalog import PizzeriaConfig
from app.models.whatsapp import WhatsAppNumber, WhatsAppSessionStatus
from app.schemas.account import PizzeriaCreate, PizzeriaRead, PizzeriaUpdate
from app.schemas.catalog import PizzeriaConfigRead, PizzeriaConfigUpdate
from app.schemas.whatsapp import WhatsAppNumberCreate, WhatsAppNumberRead, WhatsAppNumberUpdate

router = APIRouter(prefix="/pizzerias", tags=["pizzerias"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_own_pizzeria(pizzeria_id: int, account_id: int, db: DBSession) -> Pizzeria:
    """Devuelve la pizzeria si pertenece a la cuenta. Lanza 404 si no existe."""
    result = await db.execute(
        select(Pizzeria).where(
            Pizzeria.id == pizzeria_id,
            Pizzeria.account_id == account_id,
            Pizzeria.is_active.is_(True),
        )
    )
    pizzeria = result.scalar_one_or_none()
    if pizzeria is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pizzeria no encontrada")
    return pizzeria


# ---------------------------------------------------------------------------
# Pizzerias CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=PizzeriaRead, status_code=status.HTTP_201_CREATED)
async def create_pizzeria(
    body: PizzeriaCreate,
    current_account: CurrentAccount,
    _: OwnerRequired,
    db: DBSession,
) -> PizzeriaRead:
    """Crea una nueva pizzeria para la cuenta autenticada."""
    pizzeria = Pizzeria(
        account_id=current_account.id,
        name=body.name,
        address=body.address,
        city=body.city,
        logo_url=body.logo_url,
    )
    db.add(pizzeria)
    await db.commit()
    await db.refresh(pizzeria)
    return PizzeriaRead.model_validate(pizzeria)


@router.get("", response_model=list[PizzeriaRead])
async def list_pizzerias(
    current_account: CurrentAccount,
    _: OwnerRequired,
    db: DBSession,
) -> list[PizzeriaRead]:
    """Lista todas las pizzerias activas de la cuenta."""
    result = await db.execute(
        select(Pizzeria).where(
            Pizzeria.account_id == current_account.id,
            Pizzeria.is_active.is_(True),
        )
    )
    return [PizzeriaRead.model_validate(p) for p in result.scalars().all()]


@router.get("/{pizzeria_id}", response_model=PizzeriaRead)
async def get_pizzeria(
    pizzeria_id: int,
    current_account: CurrentAccount,
    _: OwnerRequired,
    db: DBSession,
) -> PizzeriaRead:
    """Detalle de una pizzeria."""
    pizzeria = await _get_own_pizzeria(pizzeria_id, current_account.id, db)
    return PizzeriaRead.model_validate(pizzeria)


@router.patch("/{pizzeria_id}", response_model=PizzeriaRead)
async def update_pizzeria(
    pizzeria_id: int,
    body: PizzeriaUpdate,
    current_account: CurrentAccount,
    _: OwnerRequired,
    db: DBSession,
) -> PizzeriaRead:
    """Actualiza campos de una pizzeria."""
    pizzeria = await _get_own_pizzeria(pizzeria_id, current_account.id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(pizzeria, field, value)
    await db.commit()
    await db.refresh(pizzeria)
    return PizzeriaRead.model_validate(pizzeria)


@router.delete("/{pizzeria_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_pizzeria(
    pizzeria_id: int,
    current_account: CurrentAccount,
    _: OwnerRequired,
    db: DBSession,
) -> None:
    """Desactiva una pizzeria (soft delete)."""
    pizzeria = await _get_own_pizzeria(pizzeria_id, current_account.id, db)
    pizzeria.is_active = False
    await db.commit()


# ---------------------------------------------------------------------------
# Configuracion de pizzeria
# ---------------------------------------------------------------------------

@router.get("/{pizzeria_id}/config", response_model=PizzeriaConfigRead)
async def get_pizzeria_config(
    pizzeria_id: int,
    current_account: CurrentAccount,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> PizzeriaConfigRead:
    """Obtiene la configuracion operativa de la pizzeria."""
    await _get_own_pizzeria(pizzeria_id, current_account.id, db)
    result = await db.execute(
        select(PizzeriaConfig).where(PizzeriaConfig.pizzeria_id == pizzeria_id)
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La pizzeria aun no tiene configuracion",
        )
    return PizzeriaConfigRead.model_validate(config)


@router.put("/{pizzeria_id}/config", response_model=PizzeriaConfigRead)
async def upsert_pizzeria_config(
    pizzeria_id: int,
    body: PizzeriaConfigUpdate,
    current_account: CurrentAccount,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> PizzeriaConfigRead:
    """Crea o actualiza la configuracion de la pizzeria."""
    await _get_own_pizzeria(pizzeria_id, current_account.id, db)
    result = await db.execute(
        select(PizzeriaConfig).where(PizzeriaConfig.pizzeria_id == pizzeria_id)
    )
    config = result.scalar_one_or_none()
    if config is None:
        config = PizzeriaConfig(pizzeria_id=pizzeria_id)
        db.add(config)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)
    return PizzeriaConfigRead.model_validate(config)


# ---------------------------------------------------------------------------
# Numeros WhatsApp
# ---------------------------------------------------------------------------

@router.post(
    "/{pizzeria_id}/whatsapp",
    response_model=WhatsAppNumberRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_whatsapp_number(
    pizzeria_id: int,
    body: WhatsAppNumberCreate,
    current_account: CurrentAccount,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> WhatsAppNumberRead:
    """Registra un numero de WhatsApp para la pizzeria."""
    await _get_own_pizzeria(pizzeria_id, current_account.id, db)

    # Verificar que session_name no esté duplicado (global)
    dup = await db.execute(
        select(WhatsAppNumber).where(WhatsAppNumber.session_name == body.session_name)
    )
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El session_name ya existe",
        )

    number = WhatsAppNumber(
        pizzeria_id=pizzeria_id,
        number=body.number,
        session_name=body.session_name,
        status=WhatsAppSessionStatus.disconnected,
    )
    db.add(number)
    await db.commit()
    await db.refresh(number)
    return WhatsAppNumberRead.model_validate(number)


@router.get("/{pizzeria_id}/whatsapp", response_model=list[WhatsAppNumberRead])
async def list_whatsapp_numbers(
    pizzeria_id: int,
    current_account: CurrentAccount,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> list[WhatsAppNumberRead]:
    """Lista los numeros de WhatsApp activos de la pizzeria."""
    await _get_own_pizzeria(pizzeria_id, current_account.id, db)
    result = await db.execute(
        select(WhatsAppNumber).where(
            WhatsAppNumber.pizzeria_id == pizzeria_id,
            WhatsAppNumber.is_active.is_(True),
        )
    )
    return [WhatsAppNumberRead.model_validate(n) for n in result.scalars().all()]


@router.delete(
    "/{pizzeria_id}/whatsapp/{number_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def deactivate_whatsapp_number(
    pizzeria_id: int,
    number_id: int,
    current_account: CurrentAccount,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> None:
    """Desactiva un numero de WhatsApp (soft delete)."""
    await _get_own_pizzeria(pizzeria_id, current_account.id, db)
    result = await db.execute(
        select(WhatsAppNumber).where(
            WhatsAppNumber.id == number_id,
            WhatsAppNumber.pizzeria_id == pizzeria_id,
            WhatsAppNumber.is_active.is_(True),
        )
    )
    number = result.scalar_one_or_none()
    if number is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Numero no encontrado"
        )
    number.is_active = False
    await db.commit()
