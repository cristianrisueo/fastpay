# Tests de las migraciones: coinciden con los modelos y se pueden deshacer y volver a aplicar.
import os
import subprocess
import sys
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# alembic.ini del servicio: este fichero está en tests/integration, así que se sube dos niveles
ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"

# Base de datos propia de estos tests, en el mismo contenedor: la de los demás tests no se toca
DATABASE_NAME = "migrations_check"


def run_alembic(database_url: str, *args: str) -> str:
    """
    Ejecuta un comando de Alembic contra la base de datos indicada y devuelve su salida.
    Va en un subproceso, como en conftest.py: dentro de pytest, env.py reconfiguraría los logs de todo el proceso.
    """
    with tempfile.TemporaryDirectory() as empty_dir:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), *args],
            cwd=empty_dir,
            env={**os.environ, "DATABASE_URL": database_url},
            capture_output=True,
            text=True,
        )

    assert result.returncode == 0, f"alembic {' '.join(args)} ha fallado:\n{result.stdout}\n{result.stderr}"
    return result.stdout


async def table_names(database_url: str) -> set[str]:
    """Tablas que hay en la base de datos indicada."""
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        names = set(result.scalars())
    await engine.dispose()
    return names


@pytest.fixture
async def empty_database_url(engine: AsyncEngine, database_url: str) -> AsyncIterator[str]:
    """Base de datos vacía en el mismo contenedor, creada para el test y borrada al terminar."""
    # CREATE y DROP DATABASE no pueden ir dentro de una transacción
    autocommit = engine.execution_options(isolation_level="AUTOCOMMIT")

    async with autocommit.connect() as connection:
        await connection.execute(text(f"CREATE DATABASE {DATABASE_NAME}"))

    # Misma URL que la de los tests, cambiando solo el nombre de la base de datos
    yield make_url(database_url).set(database=DATABASE_NAME).render_as_string(hide_password=False)

    async with autocommit.connect() as connection:
        await connection.execute(text(f"DROP DATABASE {DATABASE_NAME} WITH (FORCE)"))


def test_los_modelos_coinciden_con_las_migraciones(empty_database_url: str) -> None:
    """[E1-16] Con todas las migraciones aplicadas, alembic check no encuentra diferencias con los modelos."""
    run_alembic(empty_database_url, "upgrade", "head")

    assert "No new upgrade operations detected" in run_alembic(empty_database_url, "check")


async def test_las_migraciones_bajan_a_base_y_vuelven_a_subir(empty_database_url: str) -> None:
    """[E1-16] En una base de datos vacía, las migraciones suben, se deshacen hasta base y se vuelven a aplicar."""
    all_tables = {"alembic_version", "users", "outbox_events", "refresh_tokens"}

    run_alembic(empty_database_url, "upgrade", "head")
    assert await table_names(empty_database_url) == all_tables

    # Al bajar a base solo queda la tabla de control de Alembic
    run_alembic(empty_database_url, "downgrade", "base")
    assert await table_names(empty_database_url) == {"alembic_version"}

    # Y se pueden volver a aplicar desde cero
    run_alembic(empty_database_url, "upgrade", "head")
    assert await table_names(empty_database_url) == all_tables
