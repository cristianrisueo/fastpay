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


class UserOut(BaseModel):
    """Respuesta de registro: el usuario creado. Nunca incluye la contraseña ni su hash."""

    id: uuid.UUID
    email: str
