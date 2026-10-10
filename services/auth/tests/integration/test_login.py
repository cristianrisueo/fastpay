# Tests de POST /v1/login: el par de tokens, sus claims y cómo se guarda el refresh token.
import hashlib

import jwt
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def test_login_devuelve_los_tokens_y_guarda_solo_el_hash_del_refresh(
    client: AsyncClient, engine: AsyncEngine, user: dict[str, str]
) -> None:
    """[E1-07] El login responde 200 con el par de tokens; el refresh token solo se guarda como su SHA-256."""
    response = await client.post("/v1/login", json={"email": user["email"], "password": user["password"]})

    # Respuesta: los dos tokens, el tipo y la vida del access token
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "access_token": body["access_token"],
        "refresh_token": body["refresh_token"],
        "token_type": "bearer",
        "expires_in": 300,
    }

    # Claims del access token: la firma se comprueba en los tests del JWKS
    claims = jwt.decode(body["access_token"], options={"verify_signature": False})
    assert claims["sub"] == user["id"]
    assert claims["exp"] - claims["iat"] == 300

    # En la tabla está el SHA-256 del refresh token, nunca el token en claro
    async with engine.connect() as connection:
        rows = (await connection.execute(text("SELECT user_id, token_hash, used_at, revoked_at FROM refresh_tokens"))).all()
    [(user_id, token_hash, used_at, revoked_at)] = rows
    assert str(user_id) == user["id"]
    assert token_hash == hashlib.sha256(body["refresh_token"].encode()).hexdigest()
    assert token_hash != body["refresh_token"]
    assert used_at is None
    assert revoked_at is None


async def test_cada_login_abre_una_familia_nueva(client: AsyncClient, engine: AsyncEngine, user: dict[str, str]) -> None:
    """[E1-07] Dos logins del mismo usuario guardan sus refresh tokens en dos familias distintas."""
    credentials = {"email": user["email"], "password": user["password"]}
    await client.post("/v1/login", json=credentials)
    await client.post("/v1/login", json=credentials)

    async with engine.connect() as connection:
        families = (await connection.execute(text("SELECT family_id FROM refresh_tokens"))).scalars().all()

    assert len(families) == 2
    assert families[0] != families[1]


async def test_login_responde_igual_con_contrasena_incorrecta_y_con_email_desconocido(
    client: AsyncClient, engine: AsyncEngine, user: dict[str, str]
) -> None:
    """[E1-08] Contraseña incorrecta y email desconocido dan el mismo 401 INVALID_CREDENTIALS."""
    wrong_password = await client.post("/v1/login", json={"email": user["email"], "password": "otra-contraseña"})
    unknown_email = await client.post("/v1/login", json={"email": "nadie@example.com", "password": user["password"]})

    # Las dos respuestas son idénticas: no dejan saber si el email existe
    expected = {"code": "INVALID_CREDENTIALS", "detail": "Email o contraseña incorrectos"}
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json() == expected

    # No se ha emitido ningún refresh token
    async with engine.connect() as connection:
        assert await connection.scalar(text("SELECT count(*) FROM refresh_tokens")) == 0
