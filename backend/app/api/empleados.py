from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentAccount, DBSession, OwnerOrAdminRequired
from app.core.security import hash_password
from app.models.account import PanelUser, Pizzeria, PizzeriaRole, UserPizzeriaRole
from app.schemas.empleados import EMPLOYEE_ROLES, EmpleadoInvite, EmpleadoRead, EmpleadoRoleUpdate

router = APIRouter(prefix="/pizzerias/{pizzeria_id}/empleados", tags=["empleados"])


# ---------------------------------------------------------------------------
# Helper
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


def _to_empleado_read(user: PanelUser, role: PizzeriaRole) -> EmpleadoRead:
    return EmpleadoRead(
        id=user.id,
        account_id=user.account_id,
        name=user.name,
        email=user.email,
        is_active=user.is_active,
        role=role,
        created_at=user.created_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=EmpleadoRead, status_code=status.HTTP_201_CREATED)
async def invite_empleado(
    pizzeria_id: int,
    body: EmpleadoInvite,
    current_account: CurrentAccount,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> EmpleadoRead:
    """Invita un empleado a la pizzeria. Si el email ya existe como PanelUser solo asigna el rol."""
    if body.role not in EMPLOYEE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"El rol '{body.role.value}' no se puede asignar a empleados",
        )

    await _get_own_pizzeria(pizzeria_id, current_account.id, db)

    # Buscar o crear PanelUser
    result = await db.execute(select(PanelUser).where(PanelUser.email == body.email))
    user = result.scalar_one_or_none()

    if user is None:
        user = PanelUser(
            account_id=current_account.id,
            name=body.name,
            email=body.email,
            hashed_password=hash_password(body.password),
        )
        db.add(user)
        await db.flush()

    # Verificar que no tenga ya un rol en esta pizzeria
    dup = await db.execute(
        select(UserPizzeriaRole).where(
            UserPizzeriaRole.user_id == user.id,
            UserPizzeriaRole.pizzeria_id == pizzeria_id,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El empleado ya tiene un rol asignado en esta pizzeria",
        )

    role_assignment = UserPizzeriaRole(
        user_id=user.id,
        pizzeria_id=pizzeria_id,
        role=body.role,
    )
    db.add(role_assignment)
    await db.commit()
    await db.refresh(user)

    return _to_empleado_read(user, body.role)


@router.get("", response_model=list[EmpleadoRead])
async def list_empleados(
    pizzeria_id: int,
    current_account: CurrentAccount,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> list[EmpleadoRead]:
    """Lista todos los empleados activos de la pizzeria con su rol."""
    await _get_own_pizzeria(pizzeria_id, current_account.id, db)

    result = await db.execute(
        select(PanelUser, UserPizzeriaRole.role)
        .join(UserPizzeriaRole, UserPizzeriaRole.user_id == PanelUser.id)
        .where(
            UserPizzeriaRole.pizzeria_id == pizzeria_id,
            PanelUser.is_active.is_(True),
        )
    )
    return [_to_empleado_read(user, role) for user, role in result.all()]


@router.get("/{user_id}", response_model=EmpleadoRead)
async def get_empleado(
    pizzeria_id: int,
    user_id: int,
    current_account: CurrentAccount,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> EmpleadoRead:
    """Detalle de un empleado en la pizzeria."""
    await _get_own_pizzeria(pizzeria_id, current_account.id, db)

    result = await db.execute(
        select(PanelUser, UserPizzeriaRole.role)
        .join(UserPizzeriaRole, UserPizzeriaRole.user_id == PanelUser.id)
        .where(
            UserPizzeriaRole.pizzeria_id == pizzeria_id,
            PanelUser.id == user_id,
            PanelUser.is_active.is_(True),
        )
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")
    return _to_empleado_read(row[0], row[1])


@router.patch("/{user_id}", response_model=EmpleadoRead)
async def update_empleado_role(
    pizzeria_id: int,
    user_id: int,
    body: EmpleadoRoleUpdate,
    current_account: CurrentAccount,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> EmpleadoRead:
    """Cambia el rol de un empleado en la pizzeria."""
    if body.role not in EMPLOYEE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"El rol '{body.role.value}' no se puede asignar a empleados",
        )

    await _get_own_pizzeria(pizzeria_id, current_account.id, db)

    result = await db.execute(
        select(UserPizzeriaRole).where(
            UserPizzeriaRole.pizzeria_id == pizzeria_id,
            UserPizzeriaRole.user_id == user_id,
        )
    )
    assignment = result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    assignment.role = body.role
    await db.commit()

    user_result = await db.execute(select(PanelUser).where(PanelUser.id == user_id))
    user = user_result.scalar_one()
    return _to_empleado_read(user, body.role)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_empleado(
    pizzeria_id: int,
    user_id: int,
    current_account: CurrentAccount,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> None:
    """Elimina el acceso del empleado a esta pizzeria (borra UserPizzeriaRole)."""
    await _get_own_pizzeria(pizzeria_id, current_account.id, db)

    result = await db.execute(
        select(UserPizzeriaRole).where(
            UserPizzeriaRole.pizzeria_id == pizzeria_id,
            UserPizzeriaRole.user_id == user_id,
        )
    )
    assignment = result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    await db.delete(assignment)
    await db.commit()
