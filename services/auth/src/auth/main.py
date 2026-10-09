# Punto de entrada del servicio auth.
import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.core.config import get_settings
from auth.core.database import create_engine, create_session_factory, get_session
from auth.core.exception_handlers import register_exception_handlers
from auth.core.exceptions import DatabaseUnavailableError
from auth.core.logger import configure_logging
from auth.core.token_handler import TokenSigner
from auth.users.router import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    Lifespan del servicio auth: el código antes del yield se ejecuta al arrancar la API y el de después, al apagarla.
    Aquí se construyen las piezas que viven mientras la API esté en marcha (el pool de conexiones y la fábrica de sesiones)
    """

    # Lee la configuración. Si falta una variable obligatoria (DATABASE_URL), la API no arranca
    settings = get_settings()

    # Configura el logger de la aplicación para que los logs sean en formato JSON
    configure_logging(settings.log_level)

    # Un único engine (pool de conexiones) para toda la aplicación.
    # Crearlo no conecta todavía: las conexiones se abren cuando hacen falta
    engine = create_engine(settings)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    # Carga la clave privada una sola vez: si el fichero no existe, la API no arranca
    app.state.signer = TokenSigner(settings)

    # A partir de aquí la API atiende peticiones
    yield

    # Al apagar: cierra las conexiones del pool de forma limpia
    await engine.dispose()


# App global (la que apunta uvicorn con auth.main:app). Se le pasa el lifespan para que se ejecute
app = FastAPI(title="FastPay Auth Service", lifespan=lifespan)

# Registra los handlers de errores de dominio y validación en el servicio.
register_exception_handlers(app)

# Registra las rutas de la API
app.include_router(users_router)


@app.get("/health")
async def health(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
    """
    Comprueba que la API está viva y que puede hablar con PostgreSQL: ejecuta un SELECT 1.
    Un solo endpoint hace de comprobación de vida y de disponibilidad.
    """

    try:
        # Si la base de datos no contesta en 2 segundos, se da por caída
        async with asyncio.timeout(2):
            await session.execute(text("SELECT 1"))

    # OSError cubre la conexión rechazada (asyncpg no siempre la envuelve) y TimeoutError
    except (SQLAlchemyError, OSError) as exc:
        raise DatabaseUnavailableError() from exc

    return {"status": "ok"}


@app.get("/.well-known/jwks.json")
async def jwks(request: Request) -> dict[str, list[dict[str, str]]]:
    """Publica la clave pública con la que se verifican los access tokens (la usa wallet)."""

    signer: TokenSigner = request.app.state.signer
    return {"keys": [signer.public_jwk]}
