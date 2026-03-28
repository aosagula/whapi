from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

ALGORITHM = "HS256"


class TokenPayload(BaseModel):
    """Contenido del JWT."""

    account_id: int
    pizzeria_id: int | None = None
    role: str | None = None  # rol efectivo en la pizzería activa


def create_access_token(
    account_id: int,
    pizzeria_id: int | None = None,
    role: str | None = None,
) -> str:
    """Crea un JWT firmado con los datos del contexto de sesión."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(account_id),
        "account_id": account_id,
        "exp": expire,
    }
    if pizzeria_id is not None:
        payload["pizzeria_id"] = pizzeria_id
    if role is not None:
        payload["role"] = role

    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> TokenPayload:
    """Decodifica y valida un JWT. Lanza JWTError si es inválido o expirado."""
    raw = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    return TokenPayload(
        account_id=raw["account_id"],
        pizzeria_id=raw.get("pizzeria_id"),
        role=raw.get("role"),
    )
