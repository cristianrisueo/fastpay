# Modelo de la tabla refresh_tokens: los refresh tokens emitidos, guardados solo como hash.
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from auth.core.database import Base


class RefreshTokenModel(Base):
    """Tabla refresh_tokens. Una fila por refresh token emitido."""

    __tablename__ = "refresh_tokens"

    # UUID v7 generado por la aplicación
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)

    # Usuario dueño del token. La clave foránea se llama fk_refresh_tokens_user_id_users por la convención
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    # Cadena de rotación de un login. Con índice: revocar una familia entera tiene que ser rápido
    family_id: Mapped[uuid.UUID] = mapped_column(index=True)

    # SHA-256 del token en hexadecimal (64 caracteres). El token en claro nunca se guarda
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)

    # Cuándo caduca el token
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Cuándo se canjeó por otro (rotación). NULL mientras no se haya usado
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Cuándo se revocó (logout o reutilización). NULL mientras siga vivo
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))