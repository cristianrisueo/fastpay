# Firma de los access tokens: JWT con RS256 y el kid de la clave en la cabecera.
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from jwt.algorithms import RSAAlgorithm

from auth.core.config import Settings
from auth.core.exceptions import InvalidAccessTokenError


class TokenSigner:
    """Firma access tokens con la clave privada. Se crea una vez al arrancar la API."""

    def __init__(self, settings: Settings) -> None:
        """Lee la clave privada del fichero, guarda el kid y la vida del token, y prepara la clave pública"""

        self._private_key = settings.jwt_private_key_path.read_bytes()
        self._key_id = settings.jwt_key_id
        self._ttl = timedelta(seconds=settings.access_token_ttl_seconds)

        # Saca la clave pública de la privada; si el fichero no es una clave RSA, la API no arranca
        private_key = load_pem_private_key(self._private_key, password=None)
        if not isinstance(private_key, RSAPrivateKey):
            raise ValueError("La clave de JWT_PRIVATE_KEY_PATH no es una clave RSA")

        # Clave pública en formato JWK, con su kid: es lo que publica el JWKS
        jwk = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
        self.public_jwk = {"kty": "RSA", "kid": self._key_id, "use": "sig", "alg": "RS256", "n": jwk["n"], "e": jwk["e"]}

        # Clave pública: es la que verifica las firmas de los access tokens
        self._public_key = private_key.public_key()

    def sign_access_token(self, user_id: uuid.UUID) -> str:
        """Devuelve un access token para el usuario, válido durante el tiempo configurado."""

        # Crea los claims del token: quién es el usuario (sub), cuándo se emitió (iat) y cuándo caduca (exp)
        now = datetime.now(UTC)
        claims = {"sub": str(user_id), "iat": now, "exp": now + self._ttl}

        # Firma con RS256 y pone el kid de la clave en la cabecera
        return jwt.encode(claims, self._private_key, algorithm="RS256", headers={"kid": self._key_id})

    def verify_access_token(self, token: str) -> uuid.UUID:
        """Comprueba la firma y la caducidad del access token y devuelve el id del usuario."""

        # Solo acepta RS256 y exige los tres claims; cualquier fallo es el mismo 401
        try:
            claims = jwt.decode(token, self._public_key, algorithms=["RS256"], options={"require": ["exp", "iat", "sub"]})
            return uuid.UUID(claims["sub"])
        except (jwt.InvalidTokenError, ValueError) as exc:
            raise InvalidAccessTokenError() from exc


def new_refresh_token() -> tuple[str, str]:
    """Genera un refresh token aleatorio y devuelve el token y su SHA-256 (lo único que se guarda)."""
    token = secrets.token_urlsafe(32)
    return token, hash_refresh_token(token)


def hash_refresh_token(token: str) -> str:
    """SHA-256 del refresh token en hexadecimal. El refresh y el logout lo usarán para buscarlo."""
    return hashlib.sha256(token.encode()).hexdigest()
