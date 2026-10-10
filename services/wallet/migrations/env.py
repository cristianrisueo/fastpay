# Configuración de Alembic para wallet: cómo se conecta a la base de datos y qué tablas conoce.
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from wallet.accounts.models import AccountModel  # noqa: F401  (importar cada modelo registra su tabla en Base.metadata)
from wallet.core.config import DatabaseSettings
from wallet.core.database import Base
from wallet.transfers.models import IdempotencyKeyModel, TransferModel  # noqa: F401

# Configuración leída de alembic.ini
config = context.config

# La URL sale de DatabaseSettings (entorno o .env): migrar no exige las demás variables del servicio
config.set_main_option("sqlalchemy.url", DatabaseSettings().database_url)

# Configura los logs de Alembic según alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Las tablas que Alembic compara con la base de datos para generar migraciones
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Modo offline: genera el SQL sin conectarse (alembic upgrade head --sql)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Ejecuta las migraciones sobre una conexión ya abierta."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Modo online: abre una conexión async y ejecuta las migraciones en ella."""

    # Sin pool: es un proceso corto que abre una conexión y termina
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Ejecuta las migraciones y cierra la conexión
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Punto de entrada del modo online."""
    asyncio.run(run_async_migrations())


# Alembic decide el modo según el comando que lances
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
