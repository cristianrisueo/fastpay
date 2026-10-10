# Fixtures de los tests de integración: PostgreSQL real y efímero, migraciones aplicadas y la API en memoria.
import os
import subprocess
import sys
import tempfile
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.community.postgres import PostgresContainer

from auth.core.config import DatabaseSettings, Settings, get_settings
from auth.core.database import create_engine, create_session_factory
from auth.core.token_handler import TokenSigner
from auth.main import app

# alembic.ini del servicio: este fichero está en tests/integration, así que se sube dos niveles
ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def _apply_migrations(database_url: str) -> None:
    """
    Aplica las migraciones en la base de datos de pruebas, igual que make migrate (alembic upgrade head).
    Se ejecuta en un subproceso y con una carpeta vacía como directorio de trabajo, para que
    DatabaseSettings no lea el .env de desarrollo: solo debe ver la URL del contenedor.
    """
    with tempfile.TemporaryDirectory() as empty_dir:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), "upgrade", "head"],
            cwd=empty_dir,
            env={**os.environ, "DATABASE_URL": database_url},
            capture_output=True,
            text=True,
        )

    # Si alembic falla, se muestra su salida: sin esto el error sería un simple «returned non-zero exit status»
    if result.returncode != 0:
        raise RuntimeError(f"Fallo al migrar la base de datos de pruebas:\n{result.stderr}")


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """
    PostgreSQL efímero para toda la ejecución de pytest: se levanta una vez, con la misma imagen que compose.yml,
    y se destruye al terminar. Necesita Docker en marcha.
    """
    with PostgresContainer("postgres:18", driver="asyncpg") as postgres:
        url = postgres.get_connection_url()
        _apply_migrations(url)
        yield url


@pytest.fixture(scope="session")
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    """Un único engine (pool de conexiones) para todos los tests, que se cierra al terminar."""
    engine = create_engine(DatabaseSettings(database_url=database_url))
    yield engine
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_database(engine: AsyncEngine) -> AsyncIterator[None]:
    """
    Aislamiento entre tests: tras cada uno se vacían todas las tablas, así el siguiente empieza de cero.
    autouse=True: se aplica a todos los tests de esta carpeta sin tener que pedirla.
    """
    yield

    async with engine.begin() as connection:
        # Las tablas se leen del catálogo de PostgreSQL (menos la de Alembic), así no hay que mantener una lista
        result = await connection.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'alembic_version'")
        )
        tables = [f'"{row[0]}"' for row in result]

        # Con cero tablas (ahora mismo no hay ninguna) TRUNCATE sin nombres daría error
        if tables:
            await connection.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session")
def settings(database_url: str, private_key_path: Path) -> Settings:
    """
    Configuración de la API en los tests: la base de datos del contenedor y la clave temporal.
    _env_file=None: nunca lee el .env de desarrollo, aunque exista.
    """
    return Settings(_env_file=None, database_url=database_url, jwt_private_key_path=private_key_path, jwt_key_id="test-key")


@pytest.fixture(scope="session")
def signer(settings: Settings) -> TokenSigner:
    """Firmador de access tokens con la clave de test. Es el mismo que usa la API en los tests."""
    return TokenSigner(settings)


@pytest.fixture
async def client(engine: AsyncEngine, settings: Settings, signer: TokenSigner) -> AsyncIterator[AsyncClient]:
    """
    Cliente HTTP que habla con la API en el mismo proceso, sin red ni servidor.
    ASGITransport no ejecuta el lifespan, así que el engine, la fábrica de sesiones y el firmador se colocan
    aquí a mano en app.state. Cada petición abre una sesión nueva (get_session), como en producción.
    """
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.signer = signer

    # Las rutas piden la configuración con Depends(get_settings): se les da la de test, no la del .env
    app.dependency_overrides[get_settings] = lambda: settings

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client

    app.dependency_overrides.clear()


@pytest.fixture
async def user(client: AsyncClient) -> dict[str, str]:
    """Usuario registrado por la API. Devuelve su id, su email y su contraseña."""
    credentials = {"email": "ana@example.com", "password": "contraseña-segura"}

    response = await client.post("/v1/register", json=credentials)
    assert response.status_code == 201

    registered: dict[str, str] = response.json()
    return {**registered, "password": credentials["password"]}


@pytest.fixture
async def tokens(client: AsyncClient, user: dict[str, str]) -> dict[str, Any]:
    """Login del usuario: devuelve la respuesta (access_token, refresh_token, token_type y expires_in)."""
    response = await client.post("/v1/login", json={"email": user["email"], "password": user["password"]})
    assert response.status_code == 200

    body: dict[str, Any] = response.json()
    return body
