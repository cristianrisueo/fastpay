# Tests de los manejadores de errores: cada error sale con su código HTTP y la forma {"code", "detail"}.
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, Field

from wallet.core.exception_handlers import register_exception_handlers
from wallet.core.exceptions import (
    ConflictError,
    DatabaseUnavailableError,
    DomainError,
    NotFoundError,
    UnauthenticatedError,
    UnprocessableError,
)


class SampleUnauthenticatedError(UnauthenticatedError):
    """Error de prueba de la categoría 401: wallet aún no tiene ninguno concreto."""

    code = "SAMPLE_UNAUTHENTICATED"
    detail = "No autenticado"


class SampleNotFoundError(NotFoundError):
    """Error de prueba de la categoría 404: wallet aún no tiene ninguno concreto."""

    code = "SAMPLE_NOT_FOUND"
    detail = "No encontrado"


class SampleConflictError(ConflictError):
    """Error de prueba de la categoría 409: wallet aún no tiene ninguno concreto."""

    code = "SAMPLE_CONFLICT"
    detail = "Conflicto"


class SampleUnprocessableError(UnprocessableError):
    """Error de prueba de la categoría 422: wallet aún no tiene ninguno concreto."""

    code = "SAMPLE_UNPROCESSABLE"
    detail = "No se puede procesar"


class SampleIn(BaseModel):
    """Cuerpo de prueba con dos reglas de validación."""

    secret: str = Field(min_length=12)
    age: int = Field(gt=0)


def build_app(error: DomainError) -> FastAPI:
    """App mínima con los manejadores del servicio: /error lanza el error indicado y /sample valida un cuerpo."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/error")
    async def raise_error() -> None:
        raise error

    @app.post("/sample")
    async def sample(data: SampleIn) -> None:
        pass

    return app


def build_client(app: FastAPI) -> AsyncClient:
    """Cliente HTTP que habla con la app en memoria."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.parametrize(
    ("error_class", "status_code", "code"),
    [
        (SampleUnauthenticatedError, 401, "SAMPLE_UNAUTHENTICATED"),
        (SampleNotFoundError, 404, "SAMPLE_NOT_FOUND"),
        (SampleConflictError, 409, "SAMPLE_CONFLICT"),
        (SampleUnprocessableError, 422, "SAMPLE_UNPROCESSABLE"),
        (DatabaseUnavailableError, 503, "SERVICE_UNAVAILABLE"),
    ],
)
async def test_cada_categoria_de_error_sale_con_su_codigo_http(
    error_class: type[DomainError], status_code: int, code: str
) -> None:
    """[E2-01] Cada categoría de error se traduce a su código HTTP con el cuerpo {code, detail}."""
    error = error_class()

    async with build_client(build_app(error)) as client:
        response = await client.get("/error")

    assert response.status_code == status_code
    assert response.json() == {"code": code, "detail": error.detail}


async def test_el_detail_de_un_error_se_puede_cambiar_al_lanzarlo() -> None:
    """[E2-01] El detail de la clase es el de por defecto; si se pasa otro al lanzar el error, sale ese."""
    async with build_client(build_app(SampleUnprocessableError("Detalle concreto"))) as client:
        response = await client.get("/error")

    assert response.status_code == 422
    assert response.json() == {"code": "SAMPLE_UNPROCESSABLE", "detail": "Detalle concreto"}


async def test_la_validacion_responde_422_con_el_detail_en_texto_y_sin_los_valores() -> None:
    """[E2-01] Un cuerpo inválido da 422 VALIDATION_ERROR con «campo: mensaje; ...» y sin repetir lo que se envió."""
    async with build_client(build_app(SampleUnprocessableError())) as client:
        response = await client.post("/sample", json={"secret": "Secreto-123", "age": -42})

    assert response.status_code == 422
    assert response.json() == {
        "code": "VALIDATION_ERROR",
        "detail": "secret: String should have at least 12 characters; age: Input should be greater than 0",
    }

    # Los valores recibidos no aparecen en ninguna parte de la respuesta
    assert "Secreto-123" not in response.text
    assert "-42" not in response.text
