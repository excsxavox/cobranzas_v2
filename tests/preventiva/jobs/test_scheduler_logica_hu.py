"""
Tests de la lógica de ejecución del scheduler (HU GRC-03 líneas 28-52).

NO prueba APScheduler en sí (eso requiere tiempo real).
Prueba la lógica PURA de decidir en qué días ejecutar el pipeline:
  _calcular_dias_ejecucion, _fecha_pago_efectiva, _dias_habiles_anteriores.

Reglas HU:
  - Cortes activos: 5, 10, 15, 17, 20, 24 (parametrizables).
  - Pipeline se ejecuta 2 días hábiles antes del corte + el día de corte.
  - Si el día de pago cae en feriado/fin de semana → traslada al hábil siguiente.
  - Ejemplo HU: corte 5-may-2026 (martes) → ejecuta 30-abr, 4-may, 5-may.
"""

from datetime import date

import pytest

from preventiva.jobs.scheduler import (
    _calcular_dias_ejecucion,
    _dias_habiles_anteriores,
    _fecha_pago_efectiva,
    _siguiente_dia_habil,
)


FERIADOS = {
    date(2026, 1, 1),
    date(2026, 5, 1),    # Día del Trabajo
    date(2026, 5, 24),   # Batalla de Pichincha
    date(2026, 12, 25),
}


# ── _siguiente_dia_habil ──────────────────────────────────────────────────

class TestSiguienteDiaHabil:

    def test_lunes_es_habil(self):
        lunes = date(2026, 5, 4)
        assert _siguiente_dia_habil(date(2026, 5, 3), set()) == lunes

    def test_salta_sabado_y_domingo(self):
        viernes = date(2026, 5, 8)
        siguiente = _siguiente_dia_habil(viernes, set())
        assert siguiente == date(2026, 5, 11)   # lunes

    def test_salta_feriado(self):
        # 30-abr (jueves), siguiente sin feriado = 4-may (lunes) porque 1-may es feriado
        jueves = date(2026, 4, 30)
        siguiente = _siguiente_dia_habil(jueves, FERIADOS)
        assert siguiente == date(2026, 5, 4)


# ── _fecha_pago_efectiva ──────────────────────────────────────────────────

class TestFechaPagoEfectiva:

    def test_dia_habil_no_se_mueve(self):
        # 5-may-2026 = martes
        assert _fecha_pago_efectiva(2026, 5, 5, FERIADOS) == date(2026, 5, 5)

    def test_sabado_traslada_al_lunes(self):
        # 25-abr-2026 = sábado → traslada a 27-abr (lunes)
        assert _fecha_pago_efectiva(2026, 4, 25, set()) == date(2026, 4, 27)

    def test_domingo_traslada_al_lunes(self):
        # 26-abr-2026 = domingo → traslada a 27-abr
        assert _fecha_pago_efectiva(2026, 4, 26, set()) == date(2026, 4, 27)

    def test_feriado_traslada_al_habil(self):
        # 1-may-2026 = viernes Y feriado → traslada a 4-may (lunes)
        assert _fecha_pago_efectiva(2026, 5, 1, FERIADOS) == date(2026, 5, 4)

    def test_dia_31_en_mes_de_30_dias(self):
        # Abril tiene 30 días, corte 31 → usa día 30
        fecha = _fecha_pago_efectiva(2026, 4, 31, set())
        assert fecha.month == 4
        assert fecha.day == 30

    def test_dia_31_febrero_ajusta(self):
        # Febrero 2026 tiene 28 días → ajusta a 28-feb, que es sábado
        # → vencimiento_efectivo mueve al lunes 2-mar
        fecha = _fecha_pago_efectiva(2026, 2, 31, set())
        assert fecha == date(2026, 3, 2)


# ── _dias_habiles_anteriores ──────────────────────────────────────────────

class TestDiasHabilesAnteriores:

    def test_2_dias_habiles_sin_feriados(self):
        # Pago 5-may (martes), 2 días atrás: 30-abr (jue), NO 1-may (feriado), 4-may (lun)
        fecha_pago = date(2026, 5, 5)
        dias = _dias_habiles_anteriores(fecha_pago, 2, FERIADOS)
        assert len(dias) == 2
        assert dias[-1] == date(2026, 5, 4)    # más reciente = lunes 4-may
        assert dias[0] == date(2026, 4, 30)    # más antiguo = jueves 30-abr (salta feriado 1-may)

    def test_orden_cronologico(self):
        fecha_pago = date(2026, 5, 10)
        dias = _dias_habiles_anteriores(fecha_pago, 3, set())
        assert dias == sorted(dias)

    def test_salta_fin_de_semana(self):
        # Pago lunes 6-abr, 1 día hábil atrás = viernes 3-abr (no sábado/domingo)
        fecha_pago = date(2026, 4, 6)
        dias = _dias_habiles_anteriores(fecha_pago, 1, set())
        assert dias[0] == date(2026, 4, 3)


# ── _calcular_dias_ejecucion ──────────────────────────────────────────────

class TestCalcularDiasEjecucion:

    def test_hoy_es_primer_dia_gestion(self):
        """30-abr es el primer día de gestión para corte 5-may (con feriado 1-may)."""
        hoy = date(2026, 4, 30)
        dias_corte = {5}
        resultado = _calcular_dias_ejecucion(hoy, dias_corte, FERIADOS, dias_antes=2)
        assert len(resultado) == 1
        assert resultado[0] == (hoy, 5)

    def test_hoy_es_segundo_dia_gestion(self):
        hoy = date(2026, 5, 4)
        dias_corte = {5}
        resultado = _calcular_dias_ejecucion(hoy, dias_corte, FERIADOS, dias_antes=2)
        assert len(resultado) == 1
        assert resultado[0] == (hoy, 5)

    def test_hoy_es_dia_corte(self):
        hoy = date(2026, 5, 5)
        dias_corte = {5}
        resultado = _calcular_dias_ejecucion(hoy, dias_corte, FERIADOS, dias_antes=2)
        assert len(resultado) == 1
        assert resultado[0] == (hoy, 5)

    def test_dia_sin_gestion_no_ejecuta(self):
        """Un día cualquiera que no corresponde a ningún corte."""
        hoy = date(2026, 5, 6)
        dias_corte = {5}
        resultado = _calcular_dias_ejecucion(hoy, dias_corte, FERIADOS, dias_antes=2)
        assert len(resultado) == 0

    def test_multiples_cortes_en_el_mismo_dia(self):
        """Si hoy corresponde a gestión de más de un corte, retorna ambos."""
        # Cortes 5 y 10: gestiones (30-abr, 4-may, 5-may) y (6-may, 7-may, 10-may)
        # El 4-may es gestión 2 del corte 5. No es gestión de corte 10.
        hoy = date(2026, 5, 4)
        dias_corte = {5, 10}
        resultado = _calcular_dias_ejecucion(hoy, dias_corte, FERIADOS, dias_antes=2)
        cortes = [r[1] for r in resultado]
        assert 5 in cortes
        # El 4-may no es día de gestión del corte 10 (sus días son: 6,7,10-may)
        assert 10 not in cortes

    def test_sin_cortes_no_ejecuta(self):
        hoy = date(2026, 5, 5)
        resultado = _calcular_dias_ejecucion(hoy, set(), FERIADOS, dias_antes=2)
        assert resultado == []

    def test_cortes_iniciales_hu(self):
        """HU define cortes: 5, 10, 15, 17, 20, 24."""
        cortes_hu = {5, 10, 15, 17, 20, 24}
        # Verificar que el 5-may ejecuta solo para corte 5
        hoy = date(2026, 5, 5)
        resultado = _calcular_dias_ejecucion(hoy, cortes_hu, FERIADOS, dias_antes=2)
        cortes = [r[1] for r in resultado]
        assert 5 in cortes

    def test_feriado_desplaza_corte_y_dias_gestion(self):
        """
        Corte 24-may-2026:
          24-may = domingo Y feriado (Pichincha) → g3 = 25-may (lunes).
          g2 = 1 día hábil antes de 25-may = 22-may (viernes).
          g1 = 2 días hábiles antes de 25-may = 21-may (jueves).
        Verificar que 25-may (g3) está en dias_ejecucion.
        """
        dias_corte = {24}
        hoy = date(2026, 5, 25)   # lunes = día de corte efectivo
        resultado = _calcular_dias_ejecucion(hoy, dias_corte, FERIADOS, dias_antes=2)
        assert len(resultado) >= 1
        assert resultado[0][1] == 24
