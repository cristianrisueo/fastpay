# Errores de dominio del servicio auth, sin nada de HTTP.
# Aquí solo se definen las categorías de errores (una por tipo de problema) y los pocos errores concretos transversales.
# Qué código HTTP corresponde a cada categoría lo decide exception_handlers.py para cada categoría.


class DomainError(Exception):
    """
    Base de todos los errores de dominio. Lleva lo que verá el cliente:
    - code: identificador (por ejemplo, un código en mayúsculas con guiones bajos).
    - detail: explicación del error en castellano.
    """

    code: str
    detail: str

    def __init__(self, detail: str | None = None) -> None:
        """El detail de la clase sirve por defecto; se puede sobrescribir al lanzar el error"""
        if detail is not None:
            self.detail = detail

        super().__init__(self.detail)


# Categorías de errores


class UnauthenticatedError(DomainError):
    """Categoría 401: no se sabe quién eres (credenciales o token inválidos, caducados o ausentes)."""


class ConflictError(DomainError):
    """Categoría 409: la operación choca con el estado actual de los datos (por ejemplo, un valor que debe ser único)."""


class UnprocessableError(DomainError):
    """Categoría 422: la petición está bien formada pero no se puede procesar tal como viene."""


class ServiceUnavailableError(DomainError):
    """Categoría 503: una dependencia de la que depende el servicio (la base de datos) no responde."""


class DatabaseUnavailableError(ServiceUnavailableError):
    """La base de datos no responde (o tarda demasiado)."""

    code = "SERVICE_UNAVAILABLE"
    detail = "Base de datos no disponible"
