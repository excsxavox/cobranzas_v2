"""
Calcula las fechas de las 3 gestiones preventivas para un corte dado.

Gestiones según HU GRC-03:
  Gestión 1: dia_corte - N días hábiles (por defecto 2)
  Gestión 2: dia_corte - 1 día hábil
  Gestión 3: dia_corte (día de pago efectivo)

Reutiliza `siguiente_dia_habil` y `vencimiento_efectivo`
de cobranzas.domain.services.dias_habiles_service (sin duplicar código).
"""

from datetime import date, timedelta
from typing import Set, Tuple

# Reutilización directa desde carteramora
from cobranzas.domain.services.dias_habiles_service import (
    es_dia_habil,
    vencimiento_efectivo,
)


def _restar_dias_habiles(fecha: date, n: int, feriados: Set[date]) -> date:
    """Retrocede `n` días hábiles desde `fecha`."""
    actual = fecha
    contador = 0
    while contador < n:
        actual -= timedelta(days=1)
        if es_dia_habil(actual, feriados):
            contador += 1
    return actual


class CalendarioGestionService:

    def __init__(self, dias_antes_gestion: int = 2) -> None:
        self._dias_antes = dias_antes_gestion

    def calcular_fechas(
        self,
        anio: int,
        mes: int,
        dia_corte: int,
        feriados: Set[date],
    ) -> Tuple[date, date, date]:
        """
        Retorna (fecha_gestion1, fecha_gestion2, fecha_gestion3).
        fecha_gestion3 = vencimiento efectivo del día de corte.
        """
        fecha_pago = vencimiento_efectivo(anio, mes, dia_corte, feriados)
        fecha_g3 = fecha_pago
        fecha_g2 = _restar_dias_habiles(fecha_pago, 1, feriados)
        fecha_g1 = _restar_dias_habiles(fecha_pago, self._dias_antes, feriados)
        return fecha_g1, fecha_g2, fecha_g3

    def numero_gestion_para(
        self,
        fecha_ejecucion: date,
        anio: int,
        mes: int,
        dia_corte: int,
        feriados: Set[date],
    ) -> int:
        """
        Determina qué gestión corresponde a la fecha_ejecucion dada.
        Retorna 1, 2 o 3. Lanza ValueError si no corresponde a ninguna.
        """
        g1, g2, g3 = self.calcular_fechas(anio, mes, dia_corte, feriados)
        if fecha_ejecucion == g1:
            return 1
        if fecha_ejecucion == g2:
            return 2
        if fecha_ejecucion >= g3:
            return 3
        raise ValueError(
            f"La fecha {fecha_ejecucion} no corresponde a ninguna gestión "
            f"del corte día={dia_corte} ({g1} / {g2} / {g3})"
        )
