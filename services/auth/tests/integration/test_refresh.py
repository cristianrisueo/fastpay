# Tests de POST /v1/refresh: rotación del refresh token y revocación de la familia si se reutiliza.
import asyncio
import uuid
from typing import Any

from httpx import AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from auth.core.token_handler import TokenSigner

INVALID_REFRESH_TOKEN = {"code": "INVALID_REFRESH_TOKEN", "detail": "Refresh token no válido"}


async def refresh(client: AsyncClient, refresh_token: str) -> Response:
    """Pide un par nuevo con el refresh token."""
    return await client.post("/v1/refresh", json={"refresh_token": refresh_token})


async def stored_tokens(engine: AsyncEngine) -> list[Any]:
    """Filas de refresh_tokens en orden de emisión: (family_id, used_at, revoked_at)."""
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT family_id, used_at, revoked_at FROM refresh_tokens ORDER BY id"))
        return list(result.all())


async def test_refresh_devuelve_un_par_nuevo_y_el_anterior_deja_de_valer(
    client: AsyncClient, engine: AsyncEngine, signer: TokenSigner, user: dict[str, str], tokens: dict[str, Any]
) -> None:
    """[E1-11] El refresh devuelve un par nuevo en la misma familia y el refresh token canjeado ya no vale."""
    response = await refresh(client, tokens["refresh_token"])

    # Par nuevo: otro refresh token y un access token del mismo usuario
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "access_token": body["access_token"],
        "refresh_token": body["refresh_token"],
        "token_type": "bearer",
        "expires_in": 300,
    }
    assert body["refresh_token"] != tokens["refresh_token"]
    assert signer.verify_access_token(body["access_token"]) == uuid.UUID(user["id"])

    # Los dos tokens son de la misma familia; el viejo queda marcado como usado
    [(old_family, old_used_at, _), (new_family, new_used_at, _)] = await stored_tokens(engine)
    assert old_family == new_family
    assert old_used_at is not None
    assert new_used_at is None

    # El refresh token viejo ya no sirve
    again = await refresh(client, tokens["refresh_token"])
    assert again.status_code == 401
    assert again.json() == INVALID_REFRESH_TOKEN


async def test_refresh_con_un_token_desconocido_responde_401(client: AsyncClient) -> None:
    """[E1-11] Un refresh token que nunca se emitió responde 401 INVALID_REFRESH_TOKEN."""
    response = await refresh(client, "token-que-no-existe")

    assert response.status_code == 401
    assert response.json() == INVALID_REFRESH_TOKEN


async def test_dos_refresh_simultaneos_con_el_mismo_token(
    client: AsyncClient, engine: AsyncEngine, tokens: dict[str, Any]
) -> None:
    """
    [E1-12] Dos refresh a la vez con el mismo token (cada petición con su sesión): uno 200 y otro 401, y la familia
    queda revocada. Limitación aceptada: el que pierde la carrera cuenta como reutilización.
    """
    responses = await asyncio.gather(refresh(client, tokens["refresh_token"]), refresh(client, tokens["refresh_token"]))

    # Solo una de las dos canjea el token
    winner, loser = sorted(responses, key=lambda response: response.status_code)
    assert (winner.status_code, loser.status_code) == (200, 401)
    assert loser.json() == INVALID_REFRESH_TOKEN

    # Toda la familia queda revocada, también el token que recibió la ganadora
    rows = await stored_tokens(engine)
    assert len(rows) == 2
    assert all(revoked_at is not None for _, _, revoked_at in rows)
    assert (await refresh(client, winner.json()["refresh_token"])).status_code == 401


async def test_reutilizar_un_refresh_token_revoca_toda_su_familia(
    client: AsyncClient, engine: AsyncEngine, tokens: dict[str, Any]
) -> None:
    """[E1-14] Canjear otra vez un refresh token ya usado revoca su familia: el token que lo sustituyó tampoco vale."""
    first = tokens["refresh_token"]
    second = (await refresh(client, first)).json()["refresh_token"]

    # Reutilización del primero: posible robo
    reused = await refresh(client, first)
    assert reused.status_code == 401
    assert reused.json() == INVALID_REFRESH_TOKEN

    # La revocación se ha guardado aunque la respuesta fuera un 401
    assert all(revoked_at is not None for _, _, revoked_at in await stored_tokens(engine))

    # El segundo, que nunca se había usado, ya no sirve
    response = await refresh(client, second)
    assert response.status_code == 401
    assert response.json() == INVALID_REFRESH_TOKEN


async def test_refresh_con_un_token_caducado_responde_401(
    client: AsyncClient, engine: AsyncEngine, tokens: dict[str, Any]
) -> None:
    """[E1-15] Un refresh token caducado responde 401 INVALID_REFRESH_TOKEN y no se canjea."""
    # Caduca el token cambiando su fecha en la tabla
    async with engine.begin() as connection:
        await connection.execute(text("UPDATE refresh_tokens SET expires_at = now() - interval '1 second'"))

    response = await refresh(client, tokens["refresh_token"])

    assert response.status_code == 401
    assert response.json() == INVALID_REFRESH_TOKEN

    # No se marca como usado ni se emite ningún token nuevo
    [(_, used_at, _)] = await stored_tokens(engine)
    assert used_at is None
