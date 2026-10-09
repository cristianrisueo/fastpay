# Servicio de usuarios: la lógica del registro.
from sqlalchemy.ext.asyncio import AsyncSession

from auth.core.passwords import hash_password
from auth.outbox.repository import OutboxRepository
from auth.outbox.schemas import USER_REGISTERED
from auth.users.repository import UserRepository
from auth.users.schemas import RegisterIn, UserOut


class UserService:
    """Casos de uso de usuarios. Cada uno abre su propia transacción."""

    def __init__(self, session: AsyncSession) -> None:
        """Inicia el servicio recibiendo la sesión de BD"""
        self._session = session
        self._users = UserRepository(session)
        self._outbox = OutboxRepository(session)

    async def register(self, data: RegisterIn) -> UserOut:
        """Registra un usuario y devuelve sus datos públicos."""

        # Calcula el hash de la contraseña
        password_hash = await hash_password(data.password)

        # Guarda el usuario y su evento de creación en la misma transacción
        async with self._session.begin():
            user = await self._users.add_user(data.email, password_hash)
            await self._outbox.add_event(USER_REGISTERED, {"user_id": str(user.id), "email": user.email})

        return user
