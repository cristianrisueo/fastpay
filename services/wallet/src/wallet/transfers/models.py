# Modelos de las tablas transfers e idempotency_keys: las transferencias y sus claves de idempotencia.
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, PrimaryKeyConstraint, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from wallet.core.database import Base


class TransferModel(Base):
    """Tabla transfers. Una fila por transferencia hecha."""

    __tablename__ = "transfers"

    __table_args__ = (
        # El importe siempre es positivo
        CheckConstraint("amount > 0", name="amount_positive"),
        # Nadie se transfiere a sí mismo
        CheckConstraint("from_user_id <> to_user_id", name="distinct_accounts"),
        # Sostienen «mis movimientos» como emisor y como destinatario: el UUID v7 del id ordena por tiempo
        Index("ix_transfers_from_user_id", "from_user_id", "id"),
        Index("ix_transfers_to_user_id", "to_user_id", "id"),
    )

    # UUID v7 generado por la aplicación
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)

    # Cuenta que envía. La clave foránea se llama fk_transfers_from_user_id_accounts por la convención
    from_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.user_id"))

    # Cuenta que recibe. La clave foránea se llama fk_transfers_to_user_id_accounts por la convención
    to_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.user_id"))

    # Importe en créditos enteros
    amount: Mapped[int] = mapped_column(BigInteger)

    # Cuándo se hizo, con el reloj de PostgreSQL
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IdempotencyKeyModel(Base):
    """Tabla idempotency_keys. Una fila por cada Idempotency-Key que un usuario usa al transferir."""

    __tablename__ = "idempotency_keys"

    # Clave primaria compuesta con nombre explícito: la misma clave de dos usuarios no choca
    __table_args__ = (PrimaryKeyConstraint("user_id", "key", name="pk_idempotency_keys"),)

    # Usuario que envía la petición. Sin clave foránea: la clave se registra antes de buscar ninguna cuenta
    user_id: Mapped[uuid.UUID]

    # Valor de la cabecera Idempotency-Key
    key: Mapped[str] = mapped_column(String(255))

    # SHA-256 del cuerpo en hexadecimal: distingue un reintento de otra petición con la misma clave
    request_hash: Mapped[str] = mapped_column(String(64))

    # Respuesta original, que se repite en los reintentos. NULL mientras dura la transacción que la crea
    response_body: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
