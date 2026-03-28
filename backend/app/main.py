from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.comercios import router as comercios_router
from app.api.health import router as health_router
from app.core.config import settings

app = FastAPI(
    title="Whapi API",
    description="Plataforma multi-tenant de chatbot de pedidos para comercios gastronómicos.",
    version="0.1.0",
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers — se van agregando fase por fase
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(comercios_router)
