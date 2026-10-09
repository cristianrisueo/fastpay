# Configuración del servicio auth.
# Dos clases: DatabaseSettings (lo único que necesitan Alembic y los tests de base de datos) y Settings (todo lo demás).
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Configuración de la base de datos."""

    # Busca las variables de entorno inyectadas por Docker Compose y si no las encuentra, busca en el archivo .env de auth
    # Busca el nombre en mayúsculas, por ejemplo DATABASE_URL. Si no lo encuentra ni tiene valor por defecto, lanza un error.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # DSN y mostrar consultas SQL en la consola (para depuración)
    database_url: str
    sql_echo: bool = False


class Settings(DatabaseSettings):
    """
    Configuración completa de la API.
    Hereda la de la base de datos, así que se puede pasar donde se pida un DatabaseSettings.
    """

    # hide_input_in_errors: si la validación falla, el mensaje no repite el valor recibido.
    model_config = SettingsConfigDict(hide_input_in_errors=True)

    # Nivel mínimo de los logs: DEBUG, INFO, WARNING, ERROR o CRITICAL
    log_level: str = "INFO"

    # Clave privada con la que se firman los access tokens, y su identificador (kid)
    # Como hereda de DatabaseSettings donde se especifica que tiene que extraer las variables
    # del fichero .env estas variables las leerá del entorno, como el DSN de la BD
    jwt_private_key_path: Path
    jwt_key_id: str

    # Vida de los tokens: el access token en segundos y el refresh token en días
    access_token_ttl_seconds: int = 300
    refresh_token_ttl_days: int = 7


@lru_cache
def get_settings() -> Settings:
    """
    Devuelve la configuración. lru_cache guarda el resultado de la primera llamada
    y lo devuelve en las siguientes, evitando leer el archivo .env varias veces.
    """
    return Settings()
