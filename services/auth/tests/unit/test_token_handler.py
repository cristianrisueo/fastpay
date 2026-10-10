# Tests de los access tokens: firma RS256 con kid y rechazo de todo token que no sea válido.
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from auth.core.config import Settings
from auth.core.exceptions import InvalidAccessTokenError
from auth.core.token_handler import TokenSigner


@pytest.fixture(scope="module")
def settings(private_key_path: Path) -> Settings:
    """Configuración mínima para el firmador. La base de datos no se usa en estos tests."""
    return Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://sin-uso/sin-uso",
        jwt_private_key_path=private_key_path,
        jwt_key_id="unit-key",
    )


@pytest.fixture(scope="module")
def signer(settings: Settings) -> TokenSigner:
    """Firmador con la clave de test."""
    return TokenSigner(settings)


def valid_claims(user_id: uuid.UUID) -> dict[str, Any]:
    """Claims de un token que estaría vigente: solo cambia cómo se firma en cada test."""
    now = datetime.now(UTC)
    return {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=5)}


def test_firma_con_rs256_y_kid_y_se_verifica(signer: TokenSigner) -> None:
    """[E1-03] El token lleva RS256 y el kid en la cabecera, y al verificarlo devuelve el id del usuario."""
    user_id = uuid.uuid7()

    token = signer.sign_access_token(user_id)

    assert jwt.get_unverified_header(token) == {"alg": "RS256", "kid": "unit-key", "typ": "JWT"}
    assert signer.verify_access_token(token) == user_id


def test_rechaza_un_token_caducado(settings: Settings, signer: TokenSigner) -> None:
    """[E1-03] Un token firmado con la clave buena pero ya caducado no vale."""
    # Mismo firmador pero con una vida negativa: el token nace caducado
    expired_signer = TokenSigner(settings.model_copy(update={"access_token_ttl_seconds": -60}))
    token = expired_signer.sign_access_token(uuid.uuid7())

    with pytest.raises(InvalidAccessTokenError):
        signer.verify_access_token(token)


def test_rechaza_un_token_firmado_con_otra_clave(signer: TokenSigner) -> None:
    """[E1-03] Un token RS256 con el mismo kid pero firmado con otra clave privada no vale."""
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(valid_claims(uuid.uuid7()), other_key, algorithm="RS256", headers={"kid": "unit-key"})

    with pytest.raises(InvalidAccessTokenError):
        signer.verify_access_token(token)


def test_rechaza_un_token_hs256(signer: TokenSigner) -> None:
    """[E1-03] Un token firmado con HS256 (secreto compartido) no vale: solo se acepta RS256."""
    token = jwt.encode(valid_claims(uuid.uuid7()), "un-secreto-compartido-de-al-menos-32-bytes", algorithm="HS256")

    with pytest.raises(InvalidAccessTokenError):
        signer.verify_access_token(token)


def test_rechaza_un_token_sin_firma(signer: TokenSigner) -> None:
    """[E1-03] Un token con alg none (sin firma) no vale."""
    token = jwt.encode(valid_claims(uuid.uuid7()), "", algorithm="none")

    with pytest.raises(InvalidAccessTokenError):
        signer.verify_access_token(token)
