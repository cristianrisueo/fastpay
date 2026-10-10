# Tests de POST /v1/logout: revoca la familia del refresh token y responde siempre 204.
from typing import Any

from httpx import AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def logout(client: AsyncClient, refresh_token: str) -> Response:
    """Cierra la sesión del refresh token."""
    return await client.post("/v1/logout", json={"refresh_token": refresh_token})


async def refresh(client: AsyncClient, refresh_token: str) -> Response:
    """Pide un par nuevo con el refresh token."""
    return await client.post("/v1/refresh", json={"refresh_token": refresh_token})


async def test_logout_responde_204_y_el_refresh_deja_de_valer(client: AsyncClient, tokens: dict[str, Any]) -> None:
    """[E1-13] El logout responde 204 sin cuerpo y después el refresh token responde 401."""
    response = await logout(client, tokens["refresh_token"])

    assert response.status_code == 204
    assert response.content == b""

    after = await refresh(client, tokens["refresh_token"])
    assert after.status_code == 401
    assert after.json() == {"code": "INVALID_REFRESH_TOKEN", "detail": "Refresh token no válido"}


async def test_logout_revoca_la_familia_entera_y_solo_esa(
    client: AsyncClient, engine: AsyncEngine, user: dict[str, str], tokens: dict[str, Any]
) -> None:
    """[E1-13] El logout revoca todos los tokens de su familia (su login), pero no los de otro login del usuario."""
    # Rotación en la primera sesión y un segundo login (otro dispositivo)
    rotated = (await refresh(client, tokens["refresh_token"])).json()["refresh_token"]
    other_login = (await client.post("/v1/login", json={"email": user["email"], "password": user["password"]})).json()

    assert (await logout(client, rotated)).status_code == 204

    # Revocados los dos tokens de la primera familia; el del otro login sigue vivo
    async with engine.connect() as connection:
        revoked = await connection.scalar(text("SELECT count(*) FROM refresh_tokens WHERE revoked_at IS NOT NULL"))
    assert revoked == 2
    assert (await refresh(client, rotated)).status_code == 401
    assert (await refresh(client, other_login["refresh_token"])).status_code == 200


async def test_logout_repetido_o_con_token_desconocido_responde_204(client: AsyncClient, tokens: dict[str, Any]) -> None:
    """[E1-13] El logout responde siempre 204: aunque ya se hiciera antes o el token no exista."""
    first = await logout(client, tokens["refresh_token"])
    repeated = await logout(client, tokens["refresh_token"])
    unknown = await logout(client, "token-que-no-existe")

    assert first.status_code == repeated.status_code == unknown.status_code == 204
    assert first.content == repeated.content == unknown.content == b""
