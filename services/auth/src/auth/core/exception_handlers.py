# Manejadores de errores: único sitio del servicio que traduce excepciones a respuestas HTTP.
# Todo error de la API sale con la misma forma: {"code": "...", "detail": "..."}
from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from auth.core.exceptions import (
    ConflictError,
    DomainError,
    ServiceUnavailableError,
    UnauthenticatedError,
    UnprocessableError,
)

# Códigos HTTP correspondientes a cada error.
STATUS_BY_CATEGORY: dict[type[DomainError], int] = {
    UnauthenticatedError: 401,
    ConflictError: 409,
    UnprocessableError: 422,
    ServiceUnavailableError: 503,
}

# Tipo de un handler de errores: recibe la petición y la excepción, y devuelve la respuesta
ExceptionHandler = Callable[[Request, Exception], Awaitable[JSONResponse]]


def _error_response(status_code: int, code: str, detail: str) -> JSONResponse:
    """Construye un error HTTP con la forma que espera el cliente: {"code": "...", "detail": "..."}"""
    return JSONResponse(status_code=status_code, content={"code": code, "detail": detail})


def _build_domain_handler(status_code: int) -> ExceptionHandler:
    """
    Crea un handler para cada categoría. Todas hacen lo mismo salvo el código HTTP.
    """

    async def handler(request: Request, exc: Exception) -> JSONResponse:
        # Starlette solo nos pasa errores de esta categoría, pero su tipo es Exception: se afina para leer code y detail
        error = cast(DomainError, exc)
        return _error_response(status_code, error.code, error.detail)

    return handler


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Convierte el error de validación de FastAPI en un 422 con detail en texto: «campo: mensaje; campo: mensaje».
    """

    error = cast(RequestValidationError, exc)
    problemas: list[str] = []

    for fallo in error.errors():
        # loc es la ruta al campo, por ejemplo ("body", "email"). Se quita el primer elemento
        # (body, query...) para quedarse con el nombre del campo. Si solo hay uno, se deja tal cual
        ruta = fallo["loc"]
        campo = ".".join(str(parte) for parte in (ruta[1:] or ruta))
        problemas.append(f"{campo}: {fallo['msg']}")

    return _error_response(422, "VALIDATION_ERROR", "; ".join(problemas))


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos los handlers en la app. Se llama una vez, desde main.py."""

    # Un manejador por categoría. Starlette elige el más específico según la herencia:
    # un EmailAlreadyRegisteredError acaba en el manejador de ConflictError
    for category, status_code in STATUS_BY_CATEGORY.items():
        app.add_exception_handler(category, _build_domain_handler(status_code))

    app.add_exception_handler(RequestValidationError, validation_error_handler)
