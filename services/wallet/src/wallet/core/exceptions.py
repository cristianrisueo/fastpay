# Errores de dominio de wallet, sin HTTP: las categorías y los errores transversales.


class DomainError(Exception):
    """Base de los errores de dominio: code (identificador) y detail (explicación en castellano)."""

    code: str
    detail: str

    def __init__(self, detail: str | None = None) -> None:
        """Usa el detail de la clase salvo que se pase otro al lanzar el error."""
        if detail is not None:
            self.detail = detail

        super().__init__(self.detail)


# Categorías de errores: exception_handlers.py decide el código HTTP de cada una


class UnauthenticatedError(DomainError):
    """Categoría 401: no se sabe quién eres (token inválido, caducado o ausente)."""


class NotFoundError(DomainError):
    """Categoría 404: lo que se busca no existe."""


class ConflictError(DomainError):
    """Categoría 409: la operación choca con el estado actual de los datos."""


class UnprocessableError(DomainError):
    """Categoría 422: la petición está bien formada pero no se puede procesar tal como viene."""


class ServiceUnavailableError(DomainError):
    """Categoría 503: una dependencia del servicio no responde."""


# Errores transversales


class DatabaseUnavailableError(ServiceUnavailableError):
    """La base de datos no responde (o tarda demasiado)."""

    code = "SERVICE_UNAVAILABLE"
    detail = "Servicio no disponible"
