# Rutas de users: los endpoints HTTP del registro.
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth.core.database import get_session
from auth.users.schemas import RegisterIn, UserOut
from auth.users.service import UserService

# Crea el router
router = APIRouter(prefix="/v1", tags=["users"])


def get_user_service(session: Annotated[AsyncSession, Depends(get_session)]) -> UserService:
    """Crea el servicio con la sesión de la petición."""
    return UserService(session)


@router.post("/register", status_code=201)
async def register(data: RegisterIn, service: Annotated[UserService, Depends(get_user_service)]) -> UserOut:
    """Registra un usuario nuevo."""
    return await service.register(data)
