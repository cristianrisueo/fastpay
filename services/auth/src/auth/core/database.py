# Conexión a la base de datos de auth.
# Este archivo define cómo se construyen el pool de conexiones y las sesiones, y la base de las tablas.

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from auth.core.config import DatabaseSettings

# Convención de nombres para índices, restricciones únicas, claves foráneas y CHECK.
# Así todas tienen un nombre predecible y Alembic puede borrarlas al deshacer una migración.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}


class Base(DeclarativeBase):
    """
    Base es la clase de la que heredan todas las tablas.
    Al heredar, cada tabla queda registrada, y así Alembic sabe qué tablas existen.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def create_engine(settings: DatabaseSettings) -> AsyncEngine:
    """
    Engine es el pool de conexiones a Postgres. Hay uno solo para toda la aplicación.
    Crearlo no conecta todavía: las conexiones se abren cuando hacen falta y se reutilizan.
    """
    return create_async_engine(settings.database_url, echo=settings.sql_echo)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Factory crea sesiones ya configuradas, para no repetir la configuración."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """
    La sesión de base de datos se pasa a los endpoints como parámetro, y FastAPI la cierra al terminar.
    """
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory

    async with session_factory() as session:
        yield session
