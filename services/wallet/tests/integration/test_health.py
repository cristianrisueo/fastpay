# Tests de GET /health: la API responde y comprueba que llega a PostgreSQL.
from httpx import AsyncClient

from wallet.core.config import DatabaseSettings
from wallet.core.database import create_engine, create_session_factory
from wallet.main import app


async def test_health_responde_ok_con_la_base_de_datos_disponible(client: AsyncClient) -> None:
    """[E2-01] Con PostgreSQL en marcha, /health responde 200 {"status": "ok"}."""
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_responde_503_si_la_base_de_datos_no_responde(client: AsyncClient) -> None:
    """[E2-01] Con una base de datos inalcanzable, /health responde 503 SERVICE_UNAVAILABLE."""

    # Engine real que apunta a un puerto donde no escucha nadie: la conexión se rechaza
    unreachable = create_engine(
        DatabaseSettings(_env_file=None, database_url="postgresql+asyncpg://wallet:wallet@127.0.0.1:1/wallet_db")
    )

    # La fixture client de cada test vuelve a poner la fábrica de sesiones buena
    app.state.session_factory = create_session_factory(unreachable)
    try:
        response = await client.get("/health")
    finally:
        await unreachable.dispose()

    assert response.status_code == 503
    assert response.json() == {"code": "SERVICE_UNAVAILABLE", "detail": "Servicio no disponible"}
