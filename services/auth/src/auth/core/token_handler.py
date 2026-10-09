# Firma de los access tokens: JWT con RS256 y el kid de la clave en la cabecera.
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from auth.core.config import Settings


class TokenSigner:
    """Firma access tokens con la clave privada. Se crea una vez al arrancar la API."""

    def __init__(self, settings: Settings) -> None:
        """Lee la clave privada del fichero y guarda el kid y la vida del token"""

        self._private_key = settings.jwt_private_key_path.read_bytes()
        self._key_id = settings.jwt_key_id
        self._ttl = timedelta(seconds=settings.access_token_ttl_seconds)

    def sign_access_token(self, user_id: uuid.UUID) -> str:
        """Devuelve un access token para el usuario, válido durante el tiempo configurado."""

        # Crea los claims del token: quién es el usuario (sub), cuándo se emitió (iat) y cuándo caduca (exp)
        now = datetime.now(UTC)
        claims = {"sub": str(user_id), "iat": now, "exp": now + self._ttl}

        # Firma con RS256 y pone el kid de la clave en la cabecera
        return jwt.encode(claims, self._private_key, algorithm="RS256", headers={"kid": self._key_id})


def new_refresh_token() -> tuple[str, str]:
    """Genera un refresh token aleatorio y devuelve el token y su SHA-256 (lo único que se guarda)."""
    token = secrets.token_urlsafe(32)
    return token, hash_refresh_token(token)


def hash_refresh_token(token: str) -> str:
    """SHA-256 del refresh token en hexadecimal. El refresh y el logout lo usarán para buscarlo."""
    return hashlib.sha256(token.encode()).hexdigest()
