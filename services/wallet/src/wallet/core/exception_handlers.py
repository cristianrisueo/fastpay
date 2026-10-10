# Manejadores de errores: único sitio que traduce excepciones a respuestas HTTP {"code": "...", "detail": "..."}.
from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from wallet.core.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthenticatedError,
    UnprocessableError,
)

# Código HTTP de cada categoría de error
STATUS_BY_CATEGORY: dict[type[DomainError], int] = {
    UnauthenticatedError: 401,
    NotFoundError: 404,
    ConflictError: 409,
    UnprocessableError: 422,
    ServiceUnavailableError: 503,
}

# Tipo de un handler de errores: recibe la petición y la excepción, y devuelve la respuesta
ExceptionHandler = Callable[[Request, Exception], Awaitable[JSONResponse]]


def _error_response(status_code: int, code: str, detail: str) -> JSONResponse:
    """Construye la respuesta de error con la forma {"code": "...", "detail": "..."}."""
    return JSONResponse(status_code=status_code, content={"code": code, "detail": detail})


def _build_domain_handler(status_code: int) -> ExceptionHandler:
    """Crea el handler de una categoría. Todos hacen lo mismo salvo el código HTTP."""

    async def handler(request: Request, exc: Exception) -> JSONResponse:
        # Starlette solo pasa errores de esta categoría, pero tipados como Exception: se afina para leer code y detail
        error = cast(DomainError, exc)
        return _error_response(status_code, error.code, error.detail)

    return handler


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Convierte el error de validación de FastAPI en un 422 con detail «campo: mensaje; campo: mensaje»."""

    error = cast(RequestValidationError, exc)
    problemas: list[str] = []

    # Por cada fallo, el campo (sin el primer elemento de loc: body, query...) y el mensaje, nunca el valor recibido
    for fallo in error.errors():
        ruta = fallo["loc"]
        campo = ".".join(str(parte) for parte in (ruta[1:] or ruta))
        problemas.append(f"{campo}: {fallo['msg']}")

    return _error_response(422, "VALIDATION_ERROR", "; ".join(problemas))


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos los handlers en la app. Se llama una vez, desde main.py."""

    # Un handler por categoría: Starlette elige el más específico según la herencia del error
    for category, status_code in STATUS_BY_CATEGORY.items():
        app.add_exception_handler(category, _build_domain_handler(status_code))

    app.add_exception_handler(RequestValidationError, validation_error_handler)
