"""
Tests del servicio de calendario de gestión (HU GRC-03 líneas 28-52).

Reglas HU cubiertas:
  - Ejecución 2 días hábiles antes del corte + el propio día de pago.
  - Si el día de pago cae en feriado/fin de semana, traslada al siguiente hábil.
  - Ejemplo HU: corte 5-may-2026 (martes) → gestión 1=1-may, 2=4-may, 3=5-may.
    PERO 1-may es feriado (Día del Trabajo) → gestión 1=30-abr, 2=4-may, 3=5-may.
"""

from datetime import date

import pytest

from preventiva.domain.services.calendario_gestion_service import CalendarioGestionService


# Feriados de prueba (Ecuador 2026)
FERIADOS = {
    date(2026, 1, 1),    # Año nuevo
    date(2026, 5, 1),    # Día del Trabajo
    date(2026, 5, 24),   # Batalla de Pichincha
    date(2026, 12, 25),  # Navidad
}


class TestCalendarioGestionService:

    def test_corte_5_mayo_sin_feriado_en_dias_previos(self):
        """
        Corte 5-may-2026 (martes):
          2 días hábiles atrás:  1-may (feriado), 30-abr (jueves) → gestión 1 = 30-abr.
          1 día hábil atrás:     4-may (lunes)                    → gestión 2 = 4-may.
          Gestión 3:             5-may (martes)                   → gestión 3 = 5-may.
        """
        svc = CalendarioGestionService(dias_antes_gestion=2)
        g1, g2, g3 = svc.calcular_fechas(2026, 5, 5, FERIADOS)
        assert g3 == date(2026, 5, 5)
        assert g2 == date(2026, 5, 4)
        assert g1 == date(2026, 4, 30)   # 1-may es feriado, retrocede a 30-abr

    def test_corte_cae_sabado_traslada_al_lunes(self):
        """
        HU ejemplo: si el corte cae en sábado, se traslada al lunes.
        Gestiones: jueves, viernes, lunes.
        Corte 25-abr-2026 → sábado → traslada al 27-abr (lunes).
        """
        svc = CalendarioGestionService(dias_antes_gestion=2)
        g1, g2, g3 = svc.calcular_fechas(2026, 4, 25, set())
        assert g3 == date(2026, 4, 27)   # lunes
        assert g2 == date(2026, 4, 24)   # viernes
        assert g1 == date(2026, 4, 23)   # jueves

    def test_corte_cae_domingo_traslada_al_lunes(self):
        """Corte en domingo → traslada al lunes."""
        svc = CalendarioGestionService(dias_antes_gestion=2)
        # 26-abr-2026 = domingo
        g1, g2, g3 = svc.calcular_fechas(2026, 4, 26, set())
        assert g3 == date(2026, 4, 27)   # lunes
        assert g2 == date(2026, 4, 24)   # viernes
        assert g1 == date(2026, 4, 23)   # jueves

    def test_numero_gestion_1(self):
        svc = CalendarioGestionService(dias_antes_gestion=2)
        g1, _, _ = svc.calcular_fechas(2026, 5, 5, FERIADOS)
        assert svc.numero_gestion_para(g1, 2026, 5, 5, FERIADOS) == 1

    def test_numero_gestion_2(self):
        svc = CalendarioGestionService(dias_antes_gestion=2)
        _, g2, _ = svc.calcular_fechas(2026, 5, 5, FERIADOS)
        assert svc.numero_gestion_para(g2, 2026, 5, 5, FERIADOS) == 2

    def test_numero_gestion_3(self):
        svc = CalendarioGestionService(dias_antes_gestion=2)
        _, _, g3 = svc.calcular_fechas(2026, 5, 5, FERIADOS)
        assert svc.numero_gestion_para(g3, 2026, 5, 5, FERIADOS) == 3

    def test_fecha_fuera_de_gestion_lanza_error(self):
        """Una fecha que no corresponde a ninguna gestión lanza ValueError."""
        svc = CalendarioGestionService(dias_antes_gestion=2)
        with pytest.raises(ValueError):
            svc.numero_gestion_para(date(2026, 4, 1), 2026, 5, 5, FERIADOS)

    def test_dias_antes_parametrizable(self):
        """HU: dias_antes_gestion es parametrizable."""
        svc = CalendarioGestionService(dias_antes_gestion=3)
        g1, g2, g3 = svc.calcular_fechas(2026, 5, 5, set())
        # 5-may (martes), 3 días hábiles atrás: 30-abr
        assert g3 == date(2026, 5, 5)
        assert g1 < g2 < g3

    def test_corte_ultimo_dia_mes_febrero(self):
        """
        Corte 31 en febrero → ajusta al último día disponible (28-feb-2026).
        28-feb-2026 es sábado → vencimiento_efectivo lo mueve al lunes 2-mar-2026.
        """
        svc = CalendarioGestionService(dias_antes_gestion=2)
        g1, g2, g3 = svc.calcular_fechas(2026, 2, 31, set())
        # 28-feb = sábado → siguiente hábil = 2-mar (lunes)
        assert g3 == date(2026, 3, 2)
        assert g2 == date(2026, 2, 27)   # viernes
        assert g1 == date(2026, 2, 26)   # jueves
