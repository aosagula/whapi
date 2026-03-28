from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración central del proyecto leída desde variables de entorno."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Base de datos
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_user: str
    postgres_password: str
    postgres_db: str

    # Auth
    secret_key: str = "changeme"
    access_token_expire_minutes: int = 60

    # Webhooks
    webhook_token: str = ""  # Token compartido para validar webhooks entrantes

    # WPPConnect
    wppconnect_host: str = ""
    wppconnect_port: int = 443
    wppconnect_secret_key: str = ""

    # n8n
    n8n_host: str = ""
    n8n_port: int = 443

    # MercadoPago
    mercadopago_access_token: str = ""

    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    @property
    def database_url(self) -> str:
        """URL async para SQLAlchemy (asyncpg)."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
