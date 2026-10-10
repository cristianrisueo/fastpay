# Errores de dominio de users.
from auth.core.exceptions import ConflictError, UnauthenticatedError


class EmailAlreadyRegisteredError(ConflictError):
    """El email ya pertenece a otro usuario."""

    code = "EMAIL_ALREADY_REGISTERED"
    detail = "Este email ya está registrado"


class InvalidCredentialsError(UnauthenticatedError):
    """Email o contraseña incorrectos. Es el mismo error en los dos casos."""

    code = "INVALID_CREDENTIALS"
    detail = "Email o contraseña incorrectos"


class InvalidRefreshTokenError(UnauthenticatedError):
    """Refresh token desconocido, caducado, ya usado o revocado."""

    code = "INVALID_REFRESH_TOKEN"
    detail = "Refresh token no válido"
