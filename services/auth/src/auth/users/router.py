# Rutas de users: los endpoints HTTP de las acciones del usuario.
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth.core.config import Settings, get_settings
from auth.core.database import get_session
from auth.users.schemas import LoginIn, LoginOut, LogoutIn, RefreshIn, RegisterIn, RegisterOut
from auth.users.service import UserService

# Crea el router
router = APIRouter(prefix="/v1", tags=["users"])


def get_user_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserService:
    """Crea el servicio con la sesión de la petición y el firmador creado al arrancar la API."""
    return UserService(session, request.app.state.signer, settings)


@router.post("/register", status_code=201)
async def register(data: RegisterIn, service: Annotated[UserService, Depends(get_user_service)]) -> RegisterOut:
    """Registra un usuario nuevo."""
    return await service.register(data)


@router.post("/login")
async def login(data: LoginIn, service: Annotated[UserService, Depends(get_user_service)]) -> LoginOut:
    """Inicia sesión con email y contraseña."""
    return await service.login(data)


@router.post("/refresh")
async def refresh(data: RefreshIn, service: Annotated[UserService, Depends(get_user_service)]) -> LoginOut:
    """Renueva la sesión: cambia un refresh token por un par nuevo."""
    return await service.refresh(data)


@router.post("/logout", status_code=204)
async def logout(data: LogoutIn, service: Annotated[UserService, Depends(get_user_service)]) -> None:
    """Cierra la sesión del refresh token. Responde siempre 204, aunque el token no exista."""
    await service.logout(data)
