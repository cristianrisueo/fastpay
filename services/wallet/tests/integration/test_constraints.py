# Tests de las restricciones de la base de datos: rechazan lo que el código nunca debería escribir.
import uuid
from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from wallet.transfers.models import TransferModel

# Tipo del ayudante crear_cuenta de conftest.py
CrearCuenta = Callable[[str, int], Awaitable[uuid.UUID]]


async def insertar_transferencia(engine: AsyncEngine, origen: uuid.UUID, destino: uuid.UUID, importe: int) -> None:
    """Inserta una transferencia directamente en la tabla, sin pasar por ningún servicio."""
    async with engine.begin() as connection:
        await connection.execute(insert(TransferModel).values(from_user_id=origen, to_user_id=destino, amount=importe))


async def test_una_cuenta_no_puede_tener_saldo_negativo(crear_cuenta: CrearCuenta) -> None:
    """[E2-18] ck_accounts_balance_non_negative rechaza un saldo negativo: es la red bajo el UPDATE condicional."""
    with pytest.raises(IntegrityError, match="ck_accounts_balance_non_negative"):
        await crear_cuenta("ana@example.com", -1)


async def test_el_email_de_una_cuenta_tiene_que_estar_en_minusculas(crear_cuenta: CrearCuenta) -> None:
    """[E2-18] ck_accounts_email_lowercase rechaza un email con mayúsculas, aunque se escriba sin pasar por la API."""
    with pytest.raises(IntegrityError, match="ck_accounts_email_lowercase"):
        await crear_cuenta("Ana@Example.com", 100)


async def test_nadie_puede_transferirse_a_si_mismo(engine: AsyncEngine, crear_cuenta: CrearCuenta) -> None:
    """[E2-18] ck_transfers_distinct_accounts rechaza una transferencia con el mismo origen y destino."""
    ana = await crear_cuenta("ana@example.com", 100)

    with pytest.raises(IntegrityError, match="ck_transfers_distinct_accounts"):
        await insertar_transferencia(engine, ana, ana, 10)


async def test_una_transferencia_no_puede_ser_de_cero_creditos(engine: AsyncEngine, crear_cuenta: CrearCuenta) -> None:
    """[E2-18] ck_transfers_amount_positive rechaza un importe de 0."""
    ana = await crear_cuenta("ana@example.com", 100)
    bea = await crear_cuenta("bea@example.com", 100)

    with pytest.raises(IntegrityError, match="ck_transfers_amount_positive"):
        await insertar_transferencia(engine, ana, bea, 0)
