# Conexión a la base de datos de wallet: el pool de conexiones, las sesiones y la base de las tablas.
from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from wallet.core.config import DatabaseSettings

# Nombres predecibles para índices, únicos, claves foráneas y CHECK: así Alembic puede borrarlos al deshacer
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}


class Base(DeclarativeBase):
    """Clase de la que heredan todas las tablas. Al heredar, Alembic sabe que la tabla existe."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def create_engine(settings: DatabaseSettings) -> AsyncEngine:
    """Crea el pool de conexiones a Postgres, uno para toda la aplicación. No conecta hasta que hace falta."""
    return create_async_engine(settings.database_url, echo=settings.sql_echo)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Crea la fábrica de sesiones ya configuradas, para no repetir la configuración."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Da una sesión de base de datos a cada endpoint y la cierra al terminar la petición."""

    # La fábrica de sesiones la crea el lifespan al arrancar la API
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory

    async with session_factory() as session:
        yield session
