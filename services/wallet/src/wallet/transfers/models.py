# Modelo de la tabla transfers: las transferencias entre cuentas.
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, func
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
