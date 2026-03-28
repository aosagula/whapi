from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import TokenPayload, decode_access_token
from app.core.db import get_db
from app.models.account import Account

bearer_scheme = HTTPBearer()

CredentialsDep = Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]
DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_account(
    credentials: CredentialsDep,
    db: DBSession,
) -> Account:
    """Extrae y valida el JWT; devuelve la Account autenticada."""
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales invalidas o expiradas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise exc

    result = await db.execute(
        select(Account).where(Account.id == payload.account_id, Account.is_active.is_(True))
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise exc
    return account


async def get_token_payload(credentials: CredentialsDep) -> TokenPayload:
    """Decodifica el JWT y devuelve el payload completo."""
    try:
        return decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas o expiradas",
        )


async def get_active_pizzeria_id(
    credentials: CredentialsDep,
) -> int:
    """Extrae pizzeria_id del JWT. Falla si el token no tiene pizzeria seleccionada."""
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas o expiradas",
        )
    if payload.pizzeria_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debe seleccionar una pizzeria activa primero",
        )
    return payload.pizzeria_id


def require_role(*allowed_roles: str):
    """Fabrica una dependencia que exige uno de los roles indicados en el JWT."""

    async def _check(payload: Annotated[TokenPayload, Depends(get_token_payload)]) -> TokenPayload:
        if payload.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere uno de los roles: {', '.join(allowed_roles)}",
            )
        return payload

    return _check


CurrentAccount = Annotated[Account, Depends(get_current_account)]
ActivePizzeriaId = Annotated[int, Depends(get_active_pizzeria_id)]
TokenPayloadDep = Annotated[TokenPayload, Depends(get_token_payload)]

# Guards de rol reutilizables
OwnerRequired = Annotated[TokenPayload, Depends(require_role("owner"))]
OwnerOrAdminRequired = Annotated[TokenPayload, Depends(require_role("owner", "admin"))]
