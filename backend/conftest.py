"""Configuración de pytest: carga variables de entorno y event loop compartido."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest


def pytest_configure(config: object) -> None:
    """Carga el .env del directorio raíz antes de que se importen los módulos de la app."""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())


@pytest.fixture(scope="session")
def event_loop():
    """Event loop compartido por toda la sesión de tests (evita problemas con el pool async)."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
