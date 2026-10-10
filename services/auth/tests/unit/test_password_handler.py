# Tests del hash de contraseñas con argon2.
from auth.core.password_handler import hash_password, verify_password


async def test_verify_acepta_la_contrasena_correcta_y_rechaza_otra() -> None:
    """[E1-02] El hash verifica la contraseña con la que se calculó y no otra."""
    password_hash = await hash_password("contraseña-segura")

    assert password_hash.startswith("$argon2id$")
    assert await verify_password(password_hash, "contraseña-segura") is True
    assert await verify_password(password_hash, "contraseña-otra") is False


async def test_dos_hashes_de_la_misma_contrasena_son_distintos() -> None:
    """[E1-02] Cada hash lleva su propia sal: la misma contraseña da dos hashes distintos y los dos la verifican."""
    first = await hash_password("contraseña-segura")
    second = await hash_password("contraseña-segura")

    assert first != second
    assert await verify_password(first, "contraseña-segura") is True
    assert await verify_password(second, "contraseña-segura") is True
