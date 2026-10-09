# Repositorio del outbox: las consultas a la tabla outbox_events.
from sqlalchemy.ext.asyncio import AsyncSession

from auth.outbox.models import OutboxEventModel


class OutboxRepository:
    """Consultas del outbox. Nunca hace commit ni rollback: la transacción vive en la capa de servicio."""

    def __init__(self, session: AsyncSession) -> None:
        """Inicia el repositorio recibiendo la sesión de BD"""
        self._session = session

    async def add_event(self, event_type: str, payload: dict[str, str]) -> None:
        """Escribe un evento en la tabla outbox_events."""
        self._session.add(OutboxEventModel(type=event_type, payload=payload))
