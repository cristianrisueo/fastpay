# Logs en formato JSON, una línea por registro, con el formateador de python-json-logger.
import logging

from pythonjsonlogger.core import RESERVED_ATTRS
from pythonjsonlogger.json import JsonFormatter


def configure_logging(level: str) -> None:
    """Hace que todos los logs salgan en JSON y con el nivel indicado. Se llama desde el lifespan."""

    # Formateador JSON con ts, level, logger, message y los extra; color_message (de uvicorn) se descarta
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

    # Quita los handlers de texto de uvicorn para que sus logs suban al raíz y salgan también en JSON
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
