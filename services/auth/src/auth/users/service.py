# Servicio de usuarios: las acciones del usuario (registro e inicio de sesión).
import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from auth.core.config import Settings
from auth.core.password_handler import hash_password, verify_password
from auth.core.token_handler import TokenSigner, new_refresh_token
from auth.outbox.repository import OutboxRepository
from auth.outbox.schemas import USER_REGISTERED
from auth.tokens.repository import RefreshTokenRepository
from auth.users.exceptions import InvalidCredentialsError
from auth.users.repository import UserRepository
from auth.users.schemas import LoginIn, RegisterIn, TokenPairOut, UserOut


class UserService:
    """Acciones del usuario. Cada una abre su propia transacción."""

    def __init__(self, session: AsyncSession, signer: TokenSigner, settings: Settings) -> None:
        """Inicia el servicio con la sesión de BD, el firmador de tokens y la configuración"""
        self._session = session
        self._signer = signer
        self._users = UserRepository(session)
        self._outbox = OutboxRepository(session)
        self._tokens = RefreshTokenRepository(session)
        self._access_ttl = settings.access_token_ttl_seconds
        self._refresh_ttl = timedelta(days=settings.refresh_token_ttl_days)

    async def register(self, data: RegisterIn) -> UserOut:
        """Registra un usuario y devuelve sus datos públicos."""

        # Calcula el hash de la contraseña
        password_hash = await hash_password(data.password)

        # Guarda el usuario y su evento en la misma transacción: o se guardan los dos o ninguno
        async with self._session.begin():
            user = await self._users.add_user(data.email, password_hash)
            await self._outbox.add_event(USER_REGISTERED, {"user_id": str(user.id), "email": user.email})

        return user

    async def login(self, data: LoginIn) -> TokenPairOut:
        """Comprueba las credenciales y devuelve un access token y un refresh token nuevos."""

        async with self._session.begin():
            # Busca el usuario; si no existe o la contraseña no coincide, el mismo error en los dos casos
            user = await self._users.get_user_by_email(data.email)
            if user is None or not await verify_password(user.password_hash, data.password):
                raise InvalidCredentialsError()

            # Emite el par de tokens en una familia nueva (un login = una familia)
            return await self._issue_tokens(user.id, uuid.uuid7())

    async def _issue_tokens(self, user_id: uuid.UUID, family_id: uuid.UUID) -> TokenPairOut:
        """Guarda un refresh token nuevo y firma el access token. Lo usarán el login y el refresh."""

        # Crea el refresh token y guarda solo su hash en la familia indicada
        refresh_token, token_hash = new_refresh_token()
        await self._tokens.add_refresh_token(user_id, family_id, token_hash, self._refresh_ttl)

        # Firma el access token y devuelve el par
        access_token = self._signer.sign_access_token(user_id)
        return TokenPairOut(access_token=access_token, refresh_token=refresh_token, expires_in=self._access_ttl)
