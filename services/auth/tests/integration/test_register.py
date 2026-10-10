# Tests de POST /v1/register: alta del usuario, su hash y su evento en el outbox.
import logging
import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from auth.core.config import Settings
from auth.core.database import create_session_factory
from auth.core.password_handler import verify_password
from auth.core.token_handler import TokenSigner
from auth.users.schemas import RegisterIn
from auth.users.service import UserService

PASSWORD = "contraseña-muy-secreta"


async def fetch_all(engine: AsyncEngine, sql: str) -> list[Any]:
    """Ejecuta una consulta de lectura y devuelve sus filas."""
    async with engine.connect() as connection:
        result = await connection.execute(text(sql))
        return list(result.all())


async def test_registro_crea_el_usuario_con_su_hash_y_su_evento(
    client: AsyncClient, engine: AsyncEngine, caplog: pytest.LogCaptureFixture
) -> None:
    """[E1-04] El registro responde 201 con el email en minúsculas, guarda un hash argon2 y escribe user.registered."""
    # Captura todos los logs de la petición, de cualquier nivel
    caplog.set_level(logging.DEBUG)

    response = await client.post("/v1/register", json={"email": "Ana@Example.COM", "password": PASSWORD})

    # Respuesta: solo id y email, con el email en minúsculas
    assert response.status_code == 201
    body = response.json()
    assert body == {"id": body["id"], "email": "ana@example.com"}
    user_id = str(uuid.UUID(body["id"]))

    # En la tabla está el hash argon2 de la contraseña, nunca la contraseña
    [(email, password_hash)] = await fetch_all(engine, "SELECT email, password_hash FROM users")
    assert email == "ana@example.com"
    assert password_hash.startswith("$argon2id$")
    assert PASSWORD not in password_hash
    assert await verify_password(password_hash, PASSWORD) is True

    # Se han capturado los logs de la petición y en ninguno sale la contraseña
    assert "POST http://test/v1/register" in caplog.text
    assert PASSWORD not in caplog.text

    # El evento del alta queda en el outbox con el id y el email
    events = await fetch_all(engine, "SELECT type, payload FROM outbox_events")
    assert events == [("user.registered", {"user_id": user_id, "email": "ana@example.com"})]


async def test_registro_rechaza_un_email_repetido_aunque_cambien_las_mayusculas(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """[E1-05] Registrar un email ya usado, aunque sea con otras mayúsculas, responde 409 EMAIL_ALREADY_REGISTERED."""
    await client.post("/v1/register", json={"email": "ana@example.com", "password": PASSWORD})

    response = await client.post("/v1/register", json={"email": "ANA@example.com", "password": PASSWORD})

    assert response.status_code == 409
    assert response.json() == {"code": "EMAIL_ALREADY_REGISTERED", "detail": "Este email ya está registrado"}

    # Sigue habiendo un solo usuario y un solo evento
    assert await fetch_all(engine, "SELECT email FROM users") == [("ana@example.com",)]
    assert await fetch_all(engine, "SELECT type FROM outbox_events") == [("user.registered",)]


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"email": "no-es-un-email", "password": PASSWORD}, "email"),
        ({"email": "ana@example.com", "password": "corta"}, "password"),
        ({"email": "ana@example.com", "password": "x" * 129}, "password"),
        ({"email": "ana@example.com", "password": PASSWORD, "role": "admin"}, "role"),
    ],
    ids=["email-invalido", "password-corta", "password-larga", "campo-extra"],
)
async def test_registro_rechaza_datos_mal_formados(
    client: AsyncClient, engine: AsyncEngine, payload: dict[str, str], field: str
) -> None:
    """[E1-05] Un email inválido, una contraseña fuera de 8 a 128 o un campo extra responden 422 VALIDATION_ERROR."""
    response = await client.post("/v1/register", json=payload)

    # El detail es texto y empieza por el campo que falla
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["detail"].startswith(f"{field}: ")

    # No se ha guardado nada
    assert await fetch_all(engine, "SELECT id FROM users") == []


async def test_si_falla_el_evento_tampoco_se_guarda_el_usuario(
    engine: AsyncEngine, settings: Settings, signer: TokenSigner
) -> None:
    """[E1-06] El usuario y su evento van en la misma transacción: si no se puede escribir el evento, no queda el usuario."""
    # Restricción temporal que hace fallar cualquier INSERT en outbox_events
    async with engine.begin() as connection:
        await connection.execute(
            text("ALTER TABLE outbox_events ADD CONSTRAINT ck_outbox_events_always_fails CHECK (false)")
        )

    try:
        # Se llama al servicio directamente, con su propia sesión
        async with create_session_factory(engine)() as session:
            service = UserService(session, signer, settings)
            with pytest.raises(IntegrityError, match="ck_outbox_events_always_fails"):
                await service.register(RegisterIn(email="ana@example.com", password=PASSWORD))
    finally:
        async with engine.begin() as connection:
            await connection.execute(text("ALTER TABLE outbox_events DROP CONSTRAINT ck_outbox_events_always_fails"))

    # El INSERT del usuario se deshizo junto con el del evento
    assert await fetch_all(engine, "SELECT id FROM users") == []
