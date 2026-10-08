# Modelo de la tabla users: los usuarios registrados en auth.
import uuid

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from auth.core.database import Base


class UserModel(Base):
    """Tabla users. Una fila por usuario registrado."""

    __tablename__ = "users"

    # Restricción en la tabla: el email siempre está en minúsculas.
    # La API ya lo normaliza, pero así la tabla se protege aunque alguien escriba en ella por otro camino.
    __table_args__ = (CheckConstraint("email = lower(email)", name="email_lowercase"),)

    # UUID v7 generado por la aplicación. Es el sub del JWT y el user_id de los eventos
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)

    # Email del usuario. unique=True crea la restricción uq_users_email (el nombre sale de la convención),
    email: Mapped[str] = mapped_column(String(254), unique=True)

    # Hash de la contraseña (nunca la contraseña). Incluye la sal y los parámetros
    password_hash: Mapped[str] = mapped_column(String(255))
