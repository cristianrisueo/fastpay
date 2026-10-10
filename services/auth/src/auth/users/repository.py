# Repositorio de usuarios: las consultas a la tabla users.
import uuid

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.users.exceptions import EmailAlreadyRegisteredError
from auth.users.models import UserModel
from auth.users.schemas import RegisterOut


class UserRepository:
    """Consultas de usuarios. Nunca hace commit ni rollback: la transacción vive en la capa de servicio."""

    def __init__(self, session: AsyncSession) -> None:
        """Inicia el repositorio recibiendo la sesión de BD"""
        self._session = session

    async def add_user(self, email: str, password_hash: str) -> RegisterOut:
        """Inserta un usuario. Si el email ya existe, lanza EmailAlreadyRegisteredError."""

        # Crea un usuario siguiendo el modelo, y lo apunta como pendiente de guardar en Postgres
        model = UserModel(email=email, password_hash=password_hash)
        self._session.add(model)

        # Ejecuta el insert, captura el rechazo y comprueba que si es por email repetido u otro error
        try:
            await self._session.flush()
        except IntegrityError as exc:
            if "uq_users_email" in str(exc.orig):
                raise EmailAlreadyRegisteredError() from exc

            raise

        # Devuelve el usuario en el esquema de la API (sin hash de password)
        return RegisterOut(id=model.id, email=model.email)

    async def get_user_by_email(self, email: str) -> UserModel | None:
        """Busca un usuario por su email. Devuelve None si no existe."""
        return await self._session.scalar(select(UserModel).where(UserModel.email == email))

    async def get_user_by_id(self, user_id: uuid.UUID) -> UserModel | None:
        """Busca un usuario por su id. Devuelve None si no existe."""
        return await self._session.get(UserModel, user_id)

    async def update_email(self, user_id: uuid.UUID, email: str) -> UserModel | None:
        """Cambia el email si es distinto del actual y devuelve el usuario. None si no cambió nada."""

        # UPDATE condicional: solo cambia si el email nuevo es distinto; si ya lo tiene otro usuario, 409
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id, UserModel.email != email)
            .values(email=email)
            .returning(UserModel)
        )

        try:
            return await self._session.scalar(stmt)
        except IntegrityError as exc:
            if "uq_users_email" in str(exc.orig):
                raise EmailAlreadyRegisteredError() from exc

            raise
