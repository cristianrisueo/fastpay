# Fixtures de los tests de integración: PostgreSQL real y efímero, migraciones aplicadas y la API en memoria.
import os
import subprocess
import sys
import tempfile
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.postgres import PostgresContainer

from auth.core.config import DatabaseSettings
from auth.core.database import create_engine, create_session_factory
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


@pytest.fixture
async def client(engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """
    Cliente HTTP que habla con la API en el mismo proceso, sin red ni servidor.
    ASGITransport no ejecuta el lifespan, así que el engine y la fábrica de sesiones se colocan
    aquí a mano en app.state. Cada petición abre una sesión nueva (get_session), como en producción.
    """
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client
