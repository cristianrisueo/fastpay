# Errores específicos del dominio de users.
from auth.core.exceptions import ConflictError


class EmailAlreadyRegisteredError(ConflictError):
    """El email ya pertenece a otro usuario."""

    code = "EMAIL_ALREADY_REGISTERED"
    detail = "Este email ya está registrado"
