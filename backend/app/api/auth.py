from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.auth import create_access_token
from app.core.deps import ActivePizzeriaId, CurrentAccount, DBSession
from app.core.security import hash_password, verify_password
from app.models.account import Account, PanelUser, Pizzeria, PizzeriaRole, UserPizzeriaRole
from app.schemas.account import AccountCreate, AccountRead, PizzeriaRead
from app.schemas.auth import LoginRequest, PanelLoginRequest, PizzeriaSelectorResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: AccountCreate, db: DBSession) -> TokenResponse:
    """Registra una nueva cuenta de dueño y emite un JWT sin pizzería activa."""
    existing = await db.execute(select(Account).where(Account.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email ya está registrado",
        )

    account = Account(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        phone=body.phone,
    )
    db.add(account)
    await db.flush()  # obtener account.id antes del commit

    await db.commit()
    await db.refresh(account)

    token = create_access_token(account_id=account.id, role="owner")
    return TokenResponse(access_token=token, role="owner")


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DBSession) -> TokenResponse:
    """Autentica al usuario y devuelve un JWT sin pizzería activa."""
    result = await db.execute(
        select(Account).where(Account.email == body.email, Account.is_active.is_(True))
    )
    account = result.scalar_one_or_none()

    if account is None or not verify_password(body.password, account.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )

    token = create_access_token(account_id=account.id, role="owner")
    return TokenResponse(access_token=token, role="owner")


@router.get("/pizzerias", response_model=PizzeriaSelectorResponse)
async def list_my_pizzerias(
    current_account: CurrentAccount,
    db: DBSession,
) -> PizzeriaSelectorResponse:
    """Lista las pizzerías accesibles para el usuario autenticado."""
    result = await db.execute(
        select(Pizzeria).where(
            Pizzeria.account_id == current_account.id,
            Pizzeria.is_active.is_(True),
        )
    )
    pizzerias = result.scalars().all()
    return PizzeriaSelectorResponse(
        pizzerias=[PizzeriaRead.model_validate(p) for p in pizzerias]
    )


@router.post("/select-pizzeria/{pizzeria_id}", response_model=TokenResponse)
async def select_pizzeria(
    pizzeria_id: int,
    current_account: CurrentAccount,
    db: DBSession,
) -> TokenResponse:
    """Emite un nuevo JWT con la pizzería activa seleccionada."""
    result = await db.execute(
        select(Pizzeria).where(
            Pizzeria.id == pizzeria_id,
            Pizzeria.account_id == current_account.id,
            Pizzeria.is_active.is_(True),
        )
    )
    pizzeria = result.scalar_one_or_none()

    if pizzeria is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pizzería no encontrada o sin acceso",
        )

    # Rol efectivo: el dueño siempre tiene "owner" en sus propias pizzerías.
    # Para empleados de panel se buscaría en UserPizzeriaRole (Fase 4).
    role = "owner"

    token = create_access_token(
        account_id=current_account.id,
        pizzeria_id=pizzeria_id,
        role=role,
    )
    return TokenResponse(access_token=token, pizzeria_id=pizzeria_id, role=role)


@router.post("/panel-login", response_model=TokenResponse)
async def panel_login(body: PanelLoginRequest, db: DBSession) -> TokenResponse:
    """Login para empleados del panel (PanelUser). El token incluye pizzeria_id y rol fijo."""
    result = await db.execute(
        select(PanelUser).where(PanelUser.email == body.email, PanelUser.is_active.is_(True))
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contrasena incorrectos",
        )

    # Buscar el rol del empleado en la pizzeria solicitada
    role_result = await db.execute(
        select(UserPizzeriaRole).where(
            UserPizzeriaRole.user_id == user.id,
            UserPizzeriaRole.pizzeria_id == body.pizzeria_id,
        )
    )
    assignment = role_result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso a esta pizzeria",
        )

    token = create_access_token(
        account_id=user.account_id,
        pizzeria_id=body.pizzeria_id,
        role=assignment.role.value,
    )
    return TokenResponse(
        access_token=token,
        pizzeria_id=body.pizzeria_id,
        role=assignment.role.value,
    )


@router.get("/me", response_model=AccountRead)
async def me(current_account: CurrentAccount) -> AccountRead:
    """Devuelve los datos del usuario autenticado."""
    return AccountRead.model_validate(current_account)
