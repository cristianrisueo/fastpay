# Tests de los logs: cada línea es un JSON con sus campos.
import json
import logging
from collections.abc import Iterator
from datetime import datetime

import pytest

from auth.core.logger import configure_logging


@pytest.fixture
def restore_root_logger() -> Iterator[None]:
    """configure_logging cambia el logger raíz de todo el proceso: al terminar se dejan sus handlers y nivel como estaban."""
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level

    yield

    root.handlers = handlers
    root.setLevel(level)


@pytest.mark.usefixtures("restore_root_logger")
def test_cada_linea_de_log_es_json_con_sus_campos(capsys: pytest.CaptureFixture[str]) -> None:
    """[E1-01] Con configure_logging, una línea de log es un JSON con level, logger, message, ts y los extra."""
    configure_logging("INFO")

    logging.getLogger("auth.test").info("Usuario registrado", extra={"user_id": "123"})

    # El handler escribe en stderr una sola línea
    lines = capsys.readouterr().err.splitlines()
    assert len(lines) == 1

    record = json.loads(lines[0])
    assert record["level"] == "INFO"
    assert record["logger"] == "auth.test"
    assert record["message"] == "Usuario registrado"
    assert record["user_id"] == "123"

    # ts es una fecha ISO 8601 con zona horaria
    assert datetime.fromisoformat(record["ts"]).tzinfo is not None


@pytest.mark.usefixtures("restore_root_logger")
def test_los_logs_por_debajo_del_nivel_no_se_escriben(capsys: pytest.CaptureFixture[str]) -> None:
    """[E1-01] configure_logging fija el nivel mínimo: con WARNING, un INFO no sale."""
    configure_logging("WARNING")

    logging.getLogger("auth.test").info("No debería salir")

    assert capsys.readouterr().err == ""
