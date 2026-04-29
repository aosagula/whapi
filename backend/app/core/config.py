from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Base de datos
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    # Autenticación JWT
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # WPPConnect
    WPPCONNECT_HOST: str = ""
    WPPCONNECT_PORT: int = 443
    WPPCONNECT_SECRET_KEY: str = ""
    WPPCONNECT_WEBHOOK_URL: str = ""

    # n8n
    N8N_HOST: str = ""
    N8N_PORT: int = 443
    N8N_API_KEY: str = ""  # Clave interna para autenticar llamadas de n8n al backend

    # MercadoPago
    MERCADOPAGO_ACCESS_TOKEN: str = ""

    # LLM
    OPENAI_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url(self) -> str:
        """URL asyncpg para SQLAlchemy (uso en la app)."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        """Lista de orígenes CORS permitidos."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


settings = Settings()
