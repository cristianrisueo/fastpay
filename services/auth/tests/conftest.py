# Fixtures comunes a los tests unitarios y de integración.
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat


@pytest.fixture(scope="session")
def private_key_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """
    Clave RSA de 2048 bits para firmar los access tokens, generada una vez por ejecución en un directorio temporal.
    Así los tests no dependen de keys/ ni del .env de desarrollo.
    """
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())

    path = tmp_path_factory.mktemp("keys") / "jwt-test.pem"
    path.write_bytes(pem)
    return path
