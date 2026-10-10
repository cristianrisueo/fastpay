# Punto de entrada del servicio wallet: la app, su lifespan y /health.
import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from wallet.core.config import get_settings
from wallet.core.database import create_engine, create_session_factory, get_session
from wallet.core.exception_handlers import register_exception_handlers
from wallet.core.exceptions import DatabaseUnavailableError
from wallet.core.logger import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Crea al arrancar lo que vive mientras la API está en marcha y lo cierra al apagarla."""

    # Lee la configuración: si falta una variable obligatoria, la API no arranca
    settings = get_settings()

    # Hace que todos los logs salgan en JSON
    configure_logging(settings.log_level)

    # Un único engine (pool de conexiones) y la fábrica de sesiones para toda la aplicación
    engine = create_engine(settings)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    # A partir de aquí la API atiende peticiones
    yield

    # Al apagar, cierra las conexiones del pool
    await engine.dispose()


# App global (la que arranca uvicorn con wallet.main:app), con su lifespan
app = FastAPI(title="FastPay Wallet Service", lifespan=lifespan)

# Registra los handlers de errores de dominio y de validación
register_exception_handlers(app)


@app.get("/health")
async def health(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
    """Comprueba que la API está viva y llega a PostgreSQL con un SELECT 1."""

    # Si la base de datos falla, rechaza la conexión (OSError) o no contesta en 2 segundos, se da por caída
    try:
        async with asyncio.timeout(2):
            await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError) as exc:
        raise DatabaseUnavailableError() from exc

    return {"status": "ok"}
