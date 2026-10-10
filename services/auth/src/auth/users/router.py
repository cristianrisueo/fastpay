# Rutas de users: los endpoints HTTP de las acciones del usuario.
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from auth.core.config import Settings, get_settings
from auth.core.database import get_session
from auth.core.exceptions import InvalidAccessTokenError
from auth.core.token_handler import TokenSigner
from auth.users.schemas import (
    ChangeEmailIn,
    ChangeEmailOut,
    LoginIn,
    LoginOut,
    LogoutIn,
    RefreshIn,
    RegisterIn,
    RegisterOut,
)
from auth.users.service import UserService

# Crea el router
router = APIRouter(prefix="/v1", tags=["users"])

# Lee la cabecera Authorization: Bearer <token>. auto_error=False: sin token, el 401 lo damos nosotros con nuestro formato
bearer = HTTPBearer(auto_error=False)


def get_user_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserService:
    """Crea el servicio con la sesión de la petición y el firmador creado al arrancar la API."""
    return UserService(session, request.app.state.signer, settings)


def get_current_user_id(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> uuid.UUID:
    """Devuelve el id del usuario del access token. Sin token o con uno inválido, 401."""
    if credentials is None:
        raise InvalidAccessTokenError()

    signer: TokenSigner = request.app.state.signer
    return signer.verify_access_token(credentials.credentials)


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


@router.patch("/me/email")
async def change_email(
    data: ChangeEmailIn,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> ChangeEmailOut:
    """Cambia el email del usuario que hace la petición."""
    return await service.change_email(user_id, data)
