from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import exists, select

from app.core.deps import (
    ActivePizzeriaId,
    DBSession,
    OwnerOrAdminRequired,
)
from app.models.customer import Customer, CustomerCredit
from app.models.order import Order
from app.schemas.customer import (
    CustomerCreate,
    CustomerCreditAdjust,
    CustomerCreditRead,
    CustomerRead,
    CustomerUpdate,
)

router = APIRouter(tags=["clientes"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_customer(customer_id: int, pizzeria_id: int, db: DBSession) -> Customer:
    """Devuelve el cliente si pertenece a la pizzería activa. Lanza 404 si no."""
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.pizzeria_id == pizzeria_id,
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return customer


async def _customer_has_orders(customer_id: int, db: DBSession) -> bool:
    """Indica si el cliente tiene al menos un pedido registrado."""
    result = await db.execute(
        select(exists().where(Order.customer_id == customer_id))
    )
    return result.scalar()


# ---------------------------------------------------------------------------
# CRUD de clientes
# ---------------------------------------------------------------------------

@router.post(
    "/pizzerias/{pizzeria_id}/clientes",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_customer(
    pizzeria_id: int,
    body: CustomerCreate,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> CustomerRead:
    """Registra un nuevo cliente en la pizzería. El teléfono es único por pizzería."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    dup = await db.execute(
        select(Customer).where(
            Customer.pizzeria_id == active_pid,
            Customer.phone == body.phone,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un cliente con el teléfono '{body.phone}'",
        )

    customer = Customer(pizzeria_id=active_pid, **body.model_dump())
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return CustomerRead.model_validate(customer)


@router.get("/pizzerias/{pizzeria_id}/clientes", response_model=list[CustomerRead])
async def list_customers(
    pizzeria_id: int,
    active_pid: ActivePizzeriaId,
    db: DBSession,
    search: str | None = Query(default=None, description="Buscar por nombre o teléfono"),
) -> list[CustomerRead]:
    """Lista clientes de la pizzería. Acepta búsqueda parcial por nombre o teléfono."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    stmt = select(Customer).where(Customer.pizzeria_id == active_pid)

    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            Customer.phone.ilike(like) | Customer.name.ilike(like)
        )

    result = await db.execute(stmt.order_by(Customer.name, Customer.phone))
    return [CustomerRead.model_validate(c) for c in result.scalars()]


@router.get("/pizzerias/{pizzeria_id}/clientes/{customer_id}", response_model=CustomerRead)
async def get_customer(
    pizzeria_id: int,
    customer_id: int,
    active_pid: ActivePizzeriaId,
    db: DBSession,
) -> CustomerRead:
    """Detalle de un cliente."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    customer = await _get_customer(customer_id, active_pid, db)
    return CustomerRead.model_validate(customer)


@router.patch("/pizzerias/{pizzeria_id}/clientes/{customer_id}", response_model=CustomerRead)
async def update_customer(
    pizzeria_id: int,
    customer_id: int,
    body: CustomerUpdate,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> CustomerRead:
    """Actualiza nombre, dirección o notas de un cliente. El teléfono es inmutable."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    customer = await _get_customer(customer_id, active_pid, db)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)

    await db.commit()
    await db.refresh(customer)
    return CustomerRead.model_validate(customer)


@router.delete(
    "/pizzerias/{pizzeria_id}/clientes/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_customer(
    pizzeria_id: int,
    customer_id: int,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> None:
    """
    Elimina un cliente. Si tiene pedidos históricos rechaza la operación
    para preservar la integridad del historial.
    """
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    customer = await _get_customer(customer_id, active_pid, db)

    if await _customer_has_orders(customer_id, db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar un cliente con pedidos registrados",
        )

    await db.delete(customer)
    await db.commit()


# ---------------------------------------------------------------------------
# Créditos
# ---------------------------------------------------------------------------

@router.get(
    "/pizzerias/{pizzeria_id}/clientes/{customer_id}/credito",
    response_model=CustomerCreditRead,
)
async def get_credit(
    pizzeria_id: int,
    customer_id: int,
    active_pid: ActivePizzeriaId,
    db: DBSession,
) -> CustomerCreditRead:
    """Devuelve el saldo a favor del cliente en esta pizzería."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    await _get_customer(customer_id, active_pid, db)

    result = await db.execute(
        select(CustomerCredit).where(
            CustomerCredit.customer_id == customer_id,
            CustomerCredit.pizzeria_id == active_pid,
        )
    )
    credit = result.scalar_one_or_none()
    if credit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El cliente no tiene crédito registrado",
        )
    return CustomerCreditRead.model_validate(credit)


@router.post(
    "/pizzerias/{pizzeria_id}/clientes/{customer_id}/credito/ajuste",
    response_model=CustomerCreditRead,
)
async def adjust_credit(
    pizzeria_id: int,
    customer_id: int,
    body: CustomerCreditAdjust,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> CustomerCreditRead:
    """
    Ajusta el crédito del cliente. amount positivo agrega saldo, negativo descuenta.
    Crea el registro de crédito si no existe. No permite saldo negativo.
    """
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    await _get_customer(customer_id, active_pid, db)

    result = await db.execute(
        select(CustomerCredit).where(
            CustomerCredit.customer_id == customer_id,
            CustomerCredit.pizzeria_id == active_pid,
        )
    )
    credit = result.scalar_one_or_none()

    if credit is None:
        if body.amount < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No se puede descontar crédito: el cliente no tiene saldo",
            )
        credit = CustomerCredit(
            pizzeria_id=active_pid,
            customer_id=customer_id,
            balance=body.amount,
        )
        db.add(credit)
    else:
        new_balance = float(credit.balance) + body.amount
        if new_balance < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Saldo insuficiente. Saldo actual: {credit.balance}",
            )
        credit.balance = new_balance

    credit.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(credit)
    return CustomerCreditRead.model_validate(credit)
