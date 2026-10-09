# Repositorio de refresh tokens: las consultas a la tabla refresh_tokens.
import uuid
from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from auth.tokens.models import RefreshTokenModel


class RefreshTokenRepository:
    """Consultas de refresh tokens. Nunca hace commit ni rollback: la transacción vive en la capa de servicio."""

    def __init__(self, session: AsyncSession) -> None:
        """Inicia el repositorio recibiendo la sesión de BD"""
        self._session = session

    async def add_refresh_token(self, user_id: uuid.UUID, family_id: uuid.UUID, token_hash: str, ttl: timedelta) -> None:
        """Guarda un refresh token (solo su hash) y su caducidad."""

        # La fecha de caducidad la calcula PostgreSQL con su propio reloj: now() + ttl
        model = RefreshTokenModel(user_id=user_id, family_id=family_id, token_hash=token_hash, expires_at=func.now() + ttl)
        self._session.add(model)
