import os

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _platform_base_url() -> str:
    """URL pública del servicio cuando corre en Render (vacío en local).

    Render inyecta `RENDER_EXTERNAL_URL` (p. ej. `https://peluchi-api.onrender.com`).
    """
    raw = (
        os.environ.get("RENDER_EXTERNAL_URL")
        or os.environ.get("RENDER_EXTERNAL_HOSTNAME")
        or ""
    ).strip()
    if not raw:
        return ""
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    return raw.rstrip("/")


class Settings(BaseSettings):
    """Configuración de la aplicación leída desde .env o variables de entorno."""

    app_name: str = "Peluchi API - Tienda de peluches de coleccionista"
    app_version: str = "1.0.0"

    # Base de datos
    database_url: str = "postgresql+psycopg://peluchi:PELUCHI_DEV_PASS@localhost:5432/peluchi_db"

    # JWT
    secret_key: str = "cambia-esta-clave-secreta-por-una-larga-y-aleatoria"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""

    # URLs
    frontend_url: str = "http://localhost:8000"
    backend_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    # Seed
    admin_email: str = "admin@peluchi.es"
    admin_password: str = "admin1234"

    @field_validator("database_url", mode="before")
    @classmethod
    def _use_psycopg_driver(cls, value: str) -> str:
        """Render entrega `postgres://…`; SQLAlchemy con psycopg3 exige `postgresql+psycopg://…`.

        Sin esta adaptación el arranque falla con «No module named 'psycopg2'».
        """
        if isinstance(value, str):
            if value.startswith("postgres://"):
                return "postgresql+psycopg://" + value[len("postgres://"):]
            if value.startswith("postgresql://"):
                return "postgresql+psycopg://" + value[len("postgresql://"):]
        return value

    @model_validator(mode="after")
    def _apply_platform_urls(self) -> "Settings":
        """Adopta la URL pública de Render si no se ha configurado otra explícita."""
        base = _platform_base_url()
        if base:
            if "localhost" in self.frontend_url:
                self.frontend_url = base
            if "localhost" in self.backend_url:
                self.backend_url = base
            if "localhost" in self.cors_origins:
                self.cors_origins = base
        # Una contraseña vacía (variable de entorno en blanco) volvería inaccesible
        # el panel de administración: se recurre al valor documentado.
        if not self.admin_password:
            self.admin_password = "admin1234"
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def github_enabled(self) -> bool:
        return bool(self.github_client_id and self.github_client_secret)

    @property
    def github_redirect_uri(self) -> str:
        return f"{self.backend_url.rstrip('/')}/api/auth/github/callback"


settings = Settings()
