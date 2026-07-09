"""
Tests del HistorialMoraHandler — ventana de 6 meses (HU GRC-03 líneas 185-196).

Regla HU:
  fecha_hasta = fecha_ejecucion
  fecha_desde = mismo día (numero_meses - 1) meses atrás.
  Ejemplo: ejecución 5-may-2026 → ventana 5-dic-2025 … 5-may-2026.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from preventiva.application.chain.historial_mora_handler import HistorialMoraHandler
from preventiva.application.chain.preventiva_context import PreventivaContext


def _make_ctx(fecha: date) -> PreventivaContext:
    return PreventivaContext(
        proceso_cod="TEST001",
        fecha_ejecucion=fecha,
        dia_corte=5,
        numero_gestion=1,
    )


def _make_handler(numero_meses=6, dias_retencion=190):
    repo = MagicMock()
    repo.purgar_anteriores_a.return_value = 0
    repo.guardar_lote.return_value = 0
    repo.obtener_promedio_por_operacion.return_value = {}
    return HistorialMoraHandler(
        historial_repo=repo,
        numero_meses=numero_meses,
        dias_retencion=dias_retencion,
    ), repo


class TestVentanaHistorial:

    def test_ejemplo_exacto_de_la_hu(self):
        """HU: ejecución 5-may-2026 → ventana 5-dic-2025 a 5-may-2026."""
        handler, repo = _make_handler(numero_meses=6)
        ctx = _make_ctx(date(2026, 5, 5))
        handler._procesar(ctx)

        args = repo.obtener_promedio_por_operacion.call_args[0]
        fecha_desde, fecha_hasta = args[1], args[2]

        assert fecha_hasta == date(2026, 5, 5)
        assert fecha_desde == date(2025, 12, 5)

    def test_ventana_incluye_hoy(self):
        """fecha_hasta siempre es la fecha de ejecución (inclusive hoy)."""
        handler, repo = _make_handler()
        hoy = date(2026, 7, 9)
        ctx = _make_ctx(hoy)
        handler._procesar(ctx)

        args = repo.obtener_promedio_por_operacion.call_args[0]
        assert args[2] == hoy

    def test_ajuste_mes_corto_febrero(self):
        """Si ejecuta el 31 de agosto y retrocede a febrero (28 días), ajusta al 28."""
        handler, repo = _make_handler(numero_meses=6)
        ctx = _make_ctx(date(2026, 8, 31))
        handler._procesar(ctx)

        args = repo.obtener_promedio_por_operacion.call_args[0]
        fecha_desde = args[1]
        assert fecha_desde.month == 3   # 8 - 5 = 3 (marzo)
        assert fecha_desde.day == 31

    def test_ajuste_mes_corto_31_a_30(self):
        """Si ejecuta el 31-jul (5 meses atrás = 28-feb no existe), ajusta al 28."""
        handler, repo = _make_handler(numero_meses=6)
        ctx = _make_ctx(date(2026, 7, 31))
        handler._procesar(ctx)

        args = repo.obtener_promedio_por_operacion.call_args[0]
        fecha_desde = args[1]
        assert fecha_desde.month == 2
        assert fecha_desde.day == 28    # febrero 2026 tiene 28 días

    def test_ventana_se_publica_en_contexto(self):
        """El handler escribe ventana_desde y ventana_hasta en el contexto."""
        handler, _ = _make_handler()
        ctx = _make_ctx(date(2026, 5, 5))
        handler._procesar(ctx)
        assert ctx.ventana_desde == date(2025, 12, 5)
        assert ctx.ventana_hasta == date(2026, 5, 5)

    def test_purga_usa_dias_retencion(self):
        """La purga se calcula como fecha_ejecucion - dias_retencion."""
        handler, repo = _make_handler(dias_retencion=180)
        ctx = _make_ctx(date(2026, 5, 5))
        handler._procesar(ctx)

        fecha_limite = repo.purgar_anteriores_a.call_args[0][0]
        from datetime import timedelta
        assert fecha_limite == date(2026, 5, 5) - timedelta(days=180)

    def test_numero_meses_parametrizable(self):
        """Con numero_meses=3 la ventana es 2 meses atrás."""
        handler, repo = _make_handler(numero_meses=3)
        ctx = _make_ctx(date(2026, 5, 5))
        handler._procesar(ctx)

        args = repo.obtener_promedio_por_operacion.call_args[0]
        fecha_desde = args[1]
        assert fecha_desde == date(2026, 3, 5)   # 5-may - 2 meses = 5-mar
