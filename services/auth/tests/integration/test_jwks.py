# Tests de GET /.well-known/jwks.json: la clave pública con la que otros servicios verifican los access tokens.
from typing import Any

import jwt
from httpx import AsyncClient


async def test_jwks_publica_la_clave_publica_rsa(client: AsyncClient) -> None:
    """[E1-09] El JWKS publica una clave RSA de firma con su kid, sin nada de la clave privada."""
    response = await client.get("/.well-known/jwks.json")

    assert response.status_code == 200
    [key] = response.json()["keys"]
    assert key == {"kty": "RSA", "kid": "test-key", "use": "sig", "alg": "RS256", "n": key["n"], "e": key["e"]}


async def test_la_clave_del_jwks_verifica_el_token_del_login(
    client: AsyncClient, user: dict[str, str], tokens: dict[str, Any]
) -> None:
    """[E1-09] Con la clave del JWKS cuyo kid es el de la cabecera, se verifica el access token del login."""
    jwks = (await client.get("/.well-known/jwks.json")).json()

    # Se elige la clave por el kid de la cabecera, como hará wallet
    kid = jwt.get_unverified_header(tokens["access_token"])["kid"]
    assert kid == "test-key"
    public_key = jwt.PyJWKSet.from_dict(jwks)[kid]

    claims = jwt.decode(tokens["access_token"], public_key, algorithms=["RS256"])
    assert claims["sub"] == user["id"]
