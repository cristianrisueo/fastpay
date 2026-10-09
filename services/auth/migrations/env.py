# Configuración de Alembic para auth: cómo se conecta a la base de datos y qué tablas conoce.
# Alembic ejecuta este fichero cada vez que lanzas un comando (upgrade, revision...).
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from auth.core.config import DatabaseSettings
from auth.core.database import Base

# Aquí se importa el modelo de CADA tabla, con este formato:
#   from auth.users.models import UserModel  # noqa: F401  (registra la tabla en Base.metadata)
# Importarlo es lo que registra la tabla en Base.metadata. Si falta, Alembic cree que la tabla no existe
from auth.outbox.models import OutboxEventModel  # noqa: F401  (registra la tabla en Base.metadata)
from auth.users.models import UserModel  # noqa: F401  (registra la tabla en Base.metadata)

# Configuración leída de alembic.ini
config = context.config

# La URL sale de config.py (del .env o del entorno), no de alembic.ini.
# Así la app y las migraciones usan siempre la misma base de datos.
# Solo DatabaseSettings: migrar no debe exigir las demás variables del servicio (claves JWT, Kafka...)
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
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # sin pool: es un proceso corto que abre una conexión y termina
    )
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
