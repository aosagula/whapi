from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import decode_access_token
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
        detail="Credenciales inválidas o expiradas",
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


async def get_active_pizzeria_id(
    credentials: CredentialsDep,
) -> int:
    """Extrae pizzeria_id del JWT. Falla si el token no tiene pizzería seleccionada."""
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas o expiradas",
        )
    if payload.pizzeria_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debe seleccionar una pizzería activa primero",
        )
    return payload.pizzeria_id


CurrentAccount = Annotated[Account, Depends(get_current_account)]
ActivePizzeriaId = Annotated[int, Depends(get_active_pizzeria_id)]
