# Modelo de la tabla accounts: la cuenta de cada usuario en wallet, con su saldo.
import uuid

from sqlalchemy import BigInteger, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from wallet.core.database import Base


class AccountModel(Base):
    """Tabla accounts. Una fila por usuario de auth."""

    __tablename__ = "accounts"

    # Restricciones de la tabla: el saldo nunca es negativo y el email siempre está en minúsculas
    __table_args__ = (
        CheckConstraint("balance >= 0", name="balance_non_negative"),
        CheckConstraint("email = lower(email)", name="email_lowercase"),
    )

    # El mismo id que el usuario tiene en auth. Sin clave foránea: users vive en otra base de datos
    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    # Copia del email de auth. unique=True crea uq_accounts_email: a cada email le corresponde una sola cuenta
    email: Mapped[str] = mapped_column(String(254), unique=True)

    # Saldo en créditos enteros
    balance: Mapped[int] = mapped_column(BigInteger)
