"""Utilidades de autenticación: JWT y hashing de contraseñas."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Genera el hash bcrypt de una contraseña."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica una contraseña contra su hash."""
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str) -> str:
    """Crea un JWT con el user_id como subject."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> str:
    """Decodifica un JWT y retorna el subject (user_id). Lanza JWTError si inválido."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    sub: str | None = payload.get("sub")
    if sub is None:
        raise JWTError("Token sin subject")
    return sub
