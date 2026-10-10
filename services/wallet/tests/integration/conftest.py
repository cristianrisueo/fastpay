# Fixtures de los tests de integración: PostgreSQL real y efímero, migraciones aplicadas y la API en memoria.
import os
import subprocess
import sys
import tempfile
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.community.postgres import PostgresContainer

from wallet.accounts.models import AccountModel
from wallet.core.config import DatabaseSettings
from wallet.core.database import create_engine, create_session_factory
from wallet.main import app

# alembic.ini del servicio: este fichero está en tests/integration, así que se sube dos niveles
ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"

# Tipo del ayudante crear_cuenta: recibe el email y el saldo y devuelve el user_id de la cuenta
CrearCuenta = Callable[[str, int], Awaitable[uuid.UUID]]


def _apply_migrations(database_url: str) -> None:
    """Aplica las migraciones como make migrate, en un subproceso y en una carpeta vacía para no leer el .env."""

    # Ejecuta alembic upgrade head contra la base de datos del contenedor
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
    """PostgreSQL efímero para toda la ejecución, con la imagen de compose.yml. Necesita Docker en marcha."""
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
    """Tras cada test vacía todas las tablas, así el siguiente empieza de cero."""
    yield

    # Lee las tablas del catálogo de PostgreSQL (menos la de Alembic) y las vacía de una vez
    async with engine.begin() as connection:
        result = await connection.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'alembic_version'")
        )
        tables = [f'"{row[0]}"' for row in result]
        await connection.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))


@pytest.fixture
async def client(engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """Cliente HTTP que habla con la API en el mismo proceso, sin red ni servidor."""

    # ASGITransport no ejecuta el lifespan: el engine y la fábrica de sesiones se colocan a mano
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client


@pytest.fixture
def crear_cuenta(engine: AsyncEngine) -> CrearCuenta:
    """Ayudante que crea cuentas con saldo directamente en la base de datos: sustituye a Kafka hasta la entrega 3."""

    async def crear(email: str, saldo: int) -> uuid.UUID:
        """Inserta una cuenta con un user_id nuevo y devuelve ese user_id."""
        user_id = uuid.uuid7()

        async with engine.begin() as connection:
            await connection.execute(insert(AccountModel).values(user_id=user_id, email=email, balance=saldo))

        return user_id

    return crear
