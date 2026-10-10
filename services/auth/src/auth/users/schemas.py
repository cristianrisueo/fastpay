# Esquemas de users: lo que entra y lo que sale por la API.
import uuid
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field


class RegisterIn(BaseModel):
    """Cuerpo de POST /v1/register."""

    # Un campo que no definido aquí es un error 422, en lugar de ignorarse
    model_config = ConfigDict(extra="forbid")

    # Email con formato correcto y en minúsculas, contraseña nunca sale en respuesta ni logs
    email: Annotated[EmailStr, AfterValidator(str.lower)]
    password: str = Field(min_length=8, max_length=128, repr=False)


class RegisterOut(BaseModel):
    """Respuesta de /v1/register: el usuario creado. Nunca incluye la contraseña ni su hash."""

    id: uuid.UUID
    email: str


class LoginIn(BaseModel):
    """Cuerpo de POST /v1/login."""

    # Un campo no definido aquí es un error 422, en lugar de ignorarse
    model_config = ConfigDict(extra="forbid")

    # Email en minúsculas para buscarlo igual que se guardó; la contraseña nunca sale en logs
    email: Annotated[EmailStr, AfterValidator(str.lower)]
    password: str = Field(repr=False)


class LoginOut(BaseModel):
    """Respuesta de POST /v1/login: el access token, el refresh token y cuánto dura el access token."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshIn(BaseModel):
    """Cuerpo de POST /v1/refresh."""

    # Un campo no definido aquí es un error 422; el token nunca sale en logs
    model_config = ConfigDict(extra="forbid")

    # Refresh token, nunca sale en los logs
    refresh_token: str = Field(repr=False)


# El logout recibe lo mismo que el refresh: el refresh token
LogoutIn = RefreshIn


class ChangeEmailIn(BaseModel):
    """Cuerpo de PATCH /v1/me/email."""

    # Un campo no definido aquí es un error 422, en lugar de ignorarse
    model_config = ConfigDict(extra="forbid")

    # Email nuevo, con formato correcto y en minúsculas
    email: Annotated[EmailStr, AfterValidator(str.lower)]


# El cambio de email devuelve lo mismo que el registro: el id y el email
ChangeEmailOut = RegisterOut
