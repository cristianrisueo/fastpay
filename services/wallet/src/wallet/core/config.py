# Configuración del servicio wallet: DatabaseSettings (Alembic y tests de base de datos) y Settings (la API).
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Configuración de la base de datos."""

    # Lee las variables del entorno (Docker Compose) y, si no están, del .env de wallet
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # DSN de la base de datos y si se muestran las consultas SQL en la consola
    database_url: str
    sql_echo: bool = False


class Settings(DatabaseSettings):
    """Configuración completa de la API. Hereda la de la base de datos."""

    # Si la validación falla, el mensaje no repite el valor recibido
    model_config = SettingsConfigDict(hide_input_in_errors=True)

    # Nivel mínimo de los logs: DEBUG, INFO, WARNING, ERROR o CRITICAL
    log_level: str = "INFO"

    # URL del JWKS de auth y segundos mínimos entre dos descargas (un kid inventado no provoca una descarga por petición)
    auth_jwks_url: str
    jwks_min_refetch_seconds: int = 30


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración. lru_cache la lee una sola vez y la reutiliza."""
    return Settings()
