# Modelo de la tabla outbox_events: los eventos pendientes de publicar en Kafka.
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from auth.core.database import Base


class OutboxEventModel(Base):
    """Tabla outbox_events. Una fila por evento pendiente; al publicarse en kafka, se borra."""

    __tablename__ = "outbox_events"

    # UUID v7 generado por la aplicación. Es el event_id que wallet usa para ignorar repetidos
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)

    # Tipo de evento, por ejemplo user.registered
    type: Mapped[str] = mapped_column(String(100))

    # Datos del evento en JSON: {"user_id": "...", "email": "..."}
    payload: Mapped[dict[str, str]] = mapped_column(JSONB)

    # Intentos de publicación fallidos. Lo usará el relay para volver a intentar publicar
    attempts: Mapped[int] = mapped_column(server_default="0")

    # Cuándo se puede intentar publicar. NULL significa evento muerto
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
