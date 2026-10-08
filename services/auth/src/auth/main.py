# Punto de entrada del servicio auth.
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from auth.core.config import get_settings
from auth.core.database import create_engine, create_session_factory
from auth.core.exception_handlers import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    Lifespan del servicio auth: el código antes del yield se ejecuta al arrancar la API y el de después, al apagarla.
    Aquí se construyen las piezas que viven mientras la API esté en marcha (el pool de conexiones y la fábrica de sesiones)
    """

    # Lee la configuración. Si falta una variable obligatoria (DATABASE_URL), la API no arranca
    settings = get_settings()

    # Un único engine (pool de conexiones) para toda la aplicación.
    # Crearlo no conecta todavía: las conexiones se abren cuando hacen falta
    engine = create_engine(settings)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    # A partir de aquí la API atiende peticiones
    yield

    # Al apagar: cierra las conexiones del pool de forma limpia
    await engine.dispose()


# App global (la que apunta uvicorn con auth.main:app). Se le pasa el lifespan para que se ejecute
app = FastAPI(title="FastPay Auth Service", lifespan=lifespan)

# Registra los handlers de errores de dominio y valicación en el servicio.
register_exception_handlers(app)
