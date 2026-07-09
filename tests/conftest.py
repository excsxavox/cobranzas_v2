"""Fixtures compartidas para todos los tests de preventiva."""

from datetime import date
from typing import Optional
from unittest.mock import MagicMock

import pytest

from preventiva.domain.models.registro_lis import (
    RegistroCadetacaco,
    RegistroCamorosico,
    RegistroSeleccion,
)


# ---------------------------------------------------------------------------
# Feriados de ejemplo (fijo para reproducibilidad)
# ---------------------------------------------------------------------------

@pytest.fixture
def feriados_ejemplo():
    """Feriados ficticios para pruebas de calendario."""
    return {
        date(2026, 1, 1),   # Año nuevo
        date(2026, 5, 1),   # Día del Trabajo
        date(2026, 5, 24),  # Batalla de Pichincha (Ecuador)
        date(2026, 12, 25), # Navidad
    }


# ---------------------------------------------------------------------------
# Registros de ejemplo
# ---------------------------------------------------------------------------

def _make_cadetacaco(
    operacion: str = "OP001",
    identificacion: str = "1700000001",
    nombre: str = "JUAN PEREZ",
    tipo_operacion: str = "CREDITO",
    dia_pago: int = 5,
    valor_cuota: float = 100.0,
    dias_mora: int = 0,
    fecha_concesion: Optional[date] = None,
) -> RegistroCadetacaco:
    return RegistroCadetacaco(
        operacion=operacion,
        identificacion=identificacion,
        nombre=nombre,
        tipo_operacion=tipo_operacion,
        dia_pago=dia_pago,
        valor_cuota=valor_cuota,
        dias_mora=dias_mora,
        fecha_concesion=fecha_concesion,
    )


def _make_seleccion(
    operacion: str = "OP001",
    identificacion: str = "1700000001",
    valor_cuota: float = 100.0,
) -> RegistroSeleccion:
    return RegistroSeleccion(
        operacion=operacion,
        identificacion=identificacion,
        nombre="TEST",
        telefono="0999999999",
        tipo_operacion="CREDITO",
        dia_pago=5,
        valor_cuota=valor_cuota,
        dias_mora_actual=0,
        fecha_concesion=None,
    )


@pytest.fixture
def make_cadetacaco():
    return _make_cadetacaco


@pytest.fixture
def make_seleccion():
    return _make_seleccion
