# Funcionalidad de passwords: calcula el hash que se guarda en la base de datos y comprueba una contraseña contra él.
import asyncio

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


async def hash_password(password: str) -> str:
    """Devuelve el hash de la contraseña. Ese texto lleva dentro la sal y los parámetros, no hay que guardar nada más."""
    return await asyncio.to_thread(PasswordHasher().hash, password)


async def verify_password(password_hash: str, password: str) -> bool:
    """Devuelve True si la contraseña corresponde al hash guardado y False si no."""

    try:
        await asyncio.to_thread(PasswordHasher().verify, password_hash, password)
    except VerifyMismatchError:
        return False

    return True
