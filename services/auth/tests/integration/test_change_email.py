# Tests de PATCH /v1/me/email: cambio de email del usuario del access token y su evento en el outbox.
import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from auth.core.config import Settings
from auth.core.token_handler import TokenSigner

UNAUTHENTICATED = {"code": "UNAUTHENTICATED", "detail": "Falta el token o no es válido"}


def bearer(access_token: str) -> dict[str, str]:
    """Cabecera Authorization con el access token."""
    return {"Authorization": f"Bearer {access_token}"}


async def stored_email(engine: AsyncEngine, user_id: str) -> str | None:
    """Email del usuario tal como está en la tabla."""
    async with engine.connect() as connection:
        email: str | None = await connection.scalar(
            text("SELECT email FROM users WHERE id = :id"), {"id": uuid.UUID(user_id)}
        )
        return email


async def email_changed_events(engine: AsyncEngine) -> list[Any]:
    """Payloads de los eventos user.email_changed del outbox."""
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT payload FROM outbox_events WHERE type = 'user.email_changed'"))
        return list(result.scalars())


async def test_cambio_de_email_responde_200_y_escribe_el_evento(
    client: AsyncClient, engine: AsyncEngine, user: dict[str, str], tokens: dict[str, Any]
) -> None:
    """[E1-10] Cambiar el email responde 200 con el email nuevo en minúsculas y escribe user.email_changed."""
    response = await client.patch(
        "/v1/me/email", json={"email": "Ana.Nueva@Example.com"}, headers=bearer(tokens["access_token"])
    )

    assert response.status_code == 200
    assert response.json() == {"id": user["id"], "email": "ana.nueva@example.com"}

    # El email cambia en la tabla y el evento lleva el id y el email nuevo
    assert await stored_email(engine, user["id"]) == "ana.nueva@example.com"
    assert await email_changed_events(engine) == [{"user_id": user["id"], "email": "ana.nueva@example.com"}]


async def test_cambiar_al_mismo_email_responde_200_sin_evento(
    client: AsyncClient, engine: AsyncEngine, user: dict[str, str], tokens: dict[str, Any]
) -> None:
    """[E1-10] Si el email ya era ese, responde 200 con los datos del usuario y no escribe ningún evento."""
    response = await client.patch("/v1/me/email", json={"email": user["email"]}, headers=bearer(tokens["access_token"]))

    assert response.status_code == 200
    assert response.json() == {"id": user["id"], "email": user["email"]}
    assert await email_changed_events(engine) == []


async def test_cambiar_al_email_de_otro_usuario_responde_409(
    client: AsyncClient, engine: AsyncEngine, user: dict[str, str], tokens: dict[str, Any]
) -> None:
    """[E1-10] Un email que ya usa otro usuario responde 409 EMAIL_ALREADY_REGISTERED y no cambia nada."""
    await client.post("/v1/register", json={"email": "bea@example.com", "password": "contraseña-de-bea"})

    response = await client.patch("/v1/me/email", json={"email": "bea@example.com"}, headers=bearer(tokens["access_token"]))

    assert response.status_code == 409
    assert response.json() == {"code": "EMAIL_ALREADY_REGISTERED", "detail": "Este email ya está registrado"}
    assert await stored_email(engine, user["id"]) == user["email"]
    assert await email_changed_events(engine) == []


async def test_cambio_de_email_sin_token_o_con_token_invalido_responde_401(
    client: AsyncClient, engine: AsyncEngine, user: dict[str, str]
) -> None:
    """[E1-10] Sin cabecera Authorization o con un token que no es un JWT válido, 401 UNAUTHENTICATED."""
    without_token = await client.patch("/v1/me/email", json={"email": "otro@example.com"})
    invalid_token = await client.patch("/v1/me/email", json={"email": "otro@example.com"}, headers=bearer("no-es-un-jwt"))

    assert without_token.status_code == invalid_token.status_code == 401
    assert without_token.json() == invalid_token.json() == UNAUTHENTICATED
    assert await stored_email(engine, user["id"]) == user["email"]


async def test_cambio_de_email_con_access_token_caducado_responde_401(
    client: AsyncClient, engine: AsyncEngine, settings: Settings, user: dict[str, str]
) -> None:
    """[E1-15] Un access token caducado (aunque la firma sea buena) responde 401 UNAUTHENTICATED."""
    # Mismo firmador que la API pero con una vida negativa: el token nace caducado
    expired_signer = TokenSigner(settings.model_copy(update={"access_token_ttl_seconds": -60}))
    expired_token = expired_signer.sign_access_token(uuid.UUID(user["id"]))

    response = await client.patch("/v1/me/email", json={"email": "otro@example.com"}, headers=bearer(expired_token))

    assert response.status_code == 401
    assert response.json() == UNAUTHENTICATED
    assert await stored_email(engine, user["id"]) == user["email"]
