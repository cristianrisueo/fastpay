# Logs en formato JSON: una línea por registro. El formateador viene de la librería python-json-logger.
import logging

from pythonjsonlogger.core import RESERVED_ATTRS
from pythonjsonlogger.json import JsonFormatter


def configure_logging(level: str) -> None:
    """Hace que todos los logs salgan en JSON y con el nivel indicado. Se llama desde el lifespan."""

    # Formateador JSON: campos de cada línea y nombre con el que salen.
    # timestamp="ts" añade la fecha de cada registro con ese nombre.
    # Los campos extra que se pasen con logger.info(..., extra={...}) se añaden solos.
    # color_message es un extra de uvicorn con códigos de color, que en JSON solo estorba
    formatter = JsonFormatter(
        ["levelname", "name", "message"],
        rename_fields={"levelname": "level", "name": "logger"},
        timestamp="ts",
        reserved_attrs=RESERVED_ATTRS + ["color_message"],
    )

    # Un único handler que escribe por consola con el formateador JSON
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # Sustituye los handlers del logger raíz por el nuestro y fija el nivel mínimo
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Uvicorn trae sus propios handlers con formato de texto. Se quitan para que sus logs
    # suban al logger raíz y salgan también en JSON
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
