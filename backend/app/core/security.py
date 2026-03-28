from __future__ import annotations

import bcrypt


def hash_password(plain: str) -> str:
    """Hashea una contraseña en texto plano usando bcrypt."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica una contraseña contra su hash bcrypt."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())
