from pydantic_settings import BaseSettings, SettingsConfigDict


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
