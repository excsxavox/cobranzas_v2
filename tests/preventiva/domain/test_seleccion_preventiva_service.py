"""
Tests del servicio de selección preventiva (HU GRC-03 líneas 54-81).

Criterios cubiertos:
  C1 — Mora promedio >= N días (por defecto 5) en últimos 6 meses.
  C2 — Pago tardío RECURRENTE: aparece con mora en >= K meses (default 5/6).
  C3 — Crédito nuevo (<= M meses desde concesión).
  C4 — Alivio financiero vigente (NOVA23, REACT23, etc.).
  Exclusión — Si ningún criterio aplica, el cliente NO se incluye.
  Parametrización — Cada criterio se puede desactivar individualmente.
"""

from datetime import date

import pytest

from preventiva.domain.services.seleccion_preventiva_service import SeleccionPreventivaService
from preventiva.domain.models.registro_lis import RegistroCadetacaco


FECHA_CORTE = date(2026, 5, 3)


def _svc(**kwargs) -> SeleccionPreventivaService:
    defaults = dict(
        umbral_mora_dias=5,
        numero_meses=6,
        antiguedad_max_meses=6,
        dias_retraso_recurrente=5,
        meses_consistencia=5,           # C2: debe aparecer con mora en >=5 de 6 meses
        tipos_alivio={"NOVA23", "REACT23", "SOLUCION", "REF23"},
    )
    defaults.update(kwargs)
    return SeleccionPreventivaService(**defaults)


def _reg(
    operacion="OP001",
    identificacion="1700000001",
    tipo_operacion="CREDITO",
    dia_pago=5,
    valor_cuota=100.0,
    dias_mora=0,
    fecha_concesion=None,
):
    return RegistroCadetacaco(
        operacion=operacion,
        identificacion=identificacion,
        nombre="TEST CLIENTE",
        tipo_operacion=tipo_operacion,
        dia_pago=dia_pago,
        valor_cuota=valor_cuota,
        dias_mora=dias_mora,
        fecha_concesion=fecha_concesion,
    )


# ── Criterio 1: mora promedio ──────────────────────────────────────────────

class TestCriterioMora:

    def test_mora_promedio_igual_umbral_incluye(self):
        """HU: mora promedio >= 5 días → incluir."""
        svc = _svc()
        res = svc.evaluar([_reg()], FECHA_CORTE, promedios_mora={"OP001": 5}, telefonos={})
        assert len(res) == 1
        assert res[0].criterio_mora is True

    def test_mora_promedio_mayor_umbral_incluye(self):
        svc = _svc()
        res = svc.evaluar([_reg()], FECHA_CORTE, promedios_mora={"OP001": 10}, telefonos={})
        assert len(res) == 1

    def test_mora_promedio_menor_umbral_no_incluye_solo_c1(self):
        """4.99 → floor = 4, no aplica (HU: 'elimina el decimal')."""
        svc = _svc(criterio_pago_tardio_activo=False, criterio_nuevo_activo=False, criterio_alivio_activo=False)
        res = svc.evaluar([_reg()], FECHA_CORTE, promedios_mora={"OP001": 4}, telefonos={})
        assert len(res) == 0

    def test_criterio_mora_desactivado_no_aplica(self):
        """Si criterio_mora_activo=False, aunque el promedio sea alto, no selecciona por C1."""
        svc = _svc(criterio_mora_activo=False, criterio_pago_tardio_activo=False,
                   criterio_nuevo_activo=False, criterio_alivio_activo=False)
        res = svc.evaluar([_reg()], FECHA_CORTE, promedios_mora={"OP001": 10}, telefonos={})
        assert len(res) == 0

    def test_sin_historial_promedio_cero(self):
        """Operación sin datos históricos → promedio = 0, no selecciona."""
        svc = _svc(criterio_pago_tardio_activo=False, criterio_nuevo_activo=False, criterio_alivio_activo=False)
        res = svc.evaluar([_reg()], FECHA_CORTE, promedios_mora={}, telefonos={})
        assert len(res) == 0


# ── Criterio 2: pago tardío recurrente (consistencia) ────────────────────

class TestCriterioPagoTardioRecurrente:
    """
    C2 aplica cuando la operación aparece con mora en >= meses_consistencia
    meses distintos dentro de la ventana (HU líneas 63-66 y 185-188).
    """

    def test_consistencia_exacta_incluye(self):
        """5 meses con mora de 6 → cumple umbral mínimo."""
        svc = _svc(criterio_mora_activo=False, criterio_nuevo_activo=False,
                   criterio_alivio_activo=False, meses_consistencia=5)
        res = svc.evaluar(
            [_reg()], FECHA_CORTE,
            promedios_mora={}, telefonos={},
            meses_con_mora={"OP001": 5},
        )
        assert len(res) == 1
        assert res[0].criterio_pago_tardio is True

    def test_consistencia_mayor_incluye(self):
        """6 meses con mora → también cumple."""
        svc = _svc(criterio_mora_activo=False, criterio_nuevo_activo=False,
                   criterio_alivio_activo=False, meses_consistencia=5)
        res = svc.evaluar(
            [_reg()], FECHA_CORTE,
            promedios_mora={}, telefonos={},
            meses_con_mora={"OP001": 6},
        )
        assert len(res) == 1

    def test_consistencia_insuficiente_no_incluye(self):
        """Solo 4 meses con mora → no cumple umbral de 5."""
        svc = _svc(criterio_mora_activo=False, criterio_nuevo_activo=False,
                   criterio_alivio_activo=False, meses_consistencia=5)
        res = svc.evaluar(
            [_reg()], FECHA_CORTE,
            promedios_mora={}, telefonos={},
            meses_con_mora={"OP001": 4},
        )
        assert len(res) == 0
        assert res == []

    def test_sin_historial_meses_cero_no_incluye(self):
        """Sin datos históricos → 0 meses con mora, no selecciona."""
        svc = _svc(criterio_mora_activo=False, criterio_nuevo_activo=False,
                   criterio_alivio_activo=False, meses_consistencia=5)
        res = svc.evaluar(
            [_reg()], FECHA_CORTE,
            promedios_mora={}, telefonos={},
            meses_con_mora={},
        )
        assert len(res) == 0

    def test_c2_independiente_de_c1(self):
        """C2 usa meses_con_mora, NO el promedio. Aunque promedio < umbral_mora,
        si hay consistencia, el cliente se incluye."""
        svc = _svc(criterio_mora_activo=False, criterio_nuevo_activo=False,
                   criterio_alivio_activo=False, meses_consistencia=5)
        res = svc.evaluar(
            [_reg()], FECHA_CORTE,
            promedios_mora={"OP001": 2},   # promedio bajo → C1 no aplica
            telefonos={},
            meses_con_mora={"OP001": 5},   # consistente → C2 sí aplica
        )
        assert len(res) == 1
        assert res[0].criterio_mora is False
        assert res[0].criterio_pago_tardio is True

    def test_c2_desactivado_no_aplica(self):
        svc = _svc(criterio_mora_activo=False, criterio_nuevo_activo=False,
                   criterio_alivio_activo=False, criterio_pago_tardio_activo=False)
        res = svc.evaluar(
            [_reg()], FECHA_CORTE,
            promedios_mora={}, telefonos={},
            meses_con_mora={"OP001": 6},
        )
        assert len(res) == 0

    def test_meses_consistencia_parametrizable(self):
        """Con umbral más bajo (3), 4 meses de mora ya son suficientes."""
        svc = _svc(criterio_mora_activo=False, criterio_nuevo_activo=False,
                   criterio_alivio_activo=False, meses_consistencia=3)
        res = svc.evaluar(
            [_reg()], FECHA_CORTE,
            promedios_mora={}, telefonos={},
            meses_con_mora={"OP001": 4},
        )
        assert len(res) == 1


# ── Criterio 3: crédito nuevo ─────────────────────────────────────────────

class TestCriterioNuevo:

    def test_credito_nuevo_exactamente_6_meses_incluye(self):
        """Concesión hace exactamente 6 meses → dentro del umbral."""
        concesion = date(2025, 11, 3)  # 6 meses antes de 2026-05-03
        svc = _svc(criterio_mora_activo=False, criterio_pago_tardio_activo=False, criterio_alivio_activo=False)
        res = svc.evaluar([_reg(fecha_concesion=concesion)], FECHA_CORTE, promedios_mora={}, telefonos={})
        assert len(res) == 1
        assert res[0].criterio_nuevo is True

    def test_credito_mayor_6_meses_no_incluye(self):
        """Concesión hace 7 meses → fuera del umbral."""
        concesion = date(2025, 10, 3)  # 7 meses antes
        svc = _svc(criterio_mora_activo=False, criterio_pago_tardio_activo=False, criterio_alivio_activo=False)
        res = svc.evaluar([_reg(fecha_concesion=concesion)], FECHA_CORTE, promedios_mora={}, telefonos={})
        assert len(res) == 0

    def test_sin_fecha_concesion_no_aplica_c3(self):
        svc = _svc(criterio_mora_activo=False, criterio_pago_tardio_activo=False, criterio_alivio_activo=False)
        res = svc.evaluar([_reg(fecha_concesion=None)], FECHA_CORTE, promedios_mora={}, telefonos={})
        assert len(res) == 0

    def test_criterio_nuevo_desactivado(self):
        concesion = date(2025, 12, 1)
        svc = _svc(criterio_mora_activo=False, criterio_pago_tardio_activo=False,
                   criterio_nuevo_activo=False, criterio_alivio_activo=False)
        res = svc.evaluar([_reg(fecha_concesion=concesion)], FECHA_CORTE, promedios_mora={}, telefonos={})
        assert len(res) == 0


# ── Criterio 4: alivio financiero ─────────────────────────────────────────

class TestCriterioAlivio:

    @pytest.mark.parametrize("tipo", ["NOVA23", "REACT23", "SOLUCION", "REF23"])
    def test_tipos_alivio_configurados_incluyen(self, tipo):
        """HU: NOVA23, REACT23, SOLUCION, REF23 → gestión preventiva."""
        svc = _svc(criterio_mora_activo=False, criterio_pago_tardio_activo=False,
                   criterio_nuevo_activo=False)
        res = svc.evaluar([_reg(tipo_operacion=tipo)], FECHA_CORTE, promedios_mora={}, telefonos={})
        assert len(res) == 1
        assert res[0].criterio_alivio is True

    def test_tipo_sin_alivio_no_aplica_c4(self):
        svc = _svc(criterio_mora_activo=False, criterio_pago_tardio_activo=False,
                   criterio_nuevo_activo=False)
        res = svc.evaluar([_reg(tipo_operacion="CREDITO")], FECHA_CORTE, promedios_mora={}, telefonos={})
        assert len(res) == 0

    def test_alivio_case_insensitive(self):
        """El tipo de operación en minúsculas también debe coincidir."""
        svc = _svc(criterio_mora_activo=False, criterio_pago_tardio_activo=False,
                   criterio_nuevo_activo=False)
        res = svc.evaluar([_reg(tipo_operacion="nova23")], FECHA_CORTE, promedios_mora={}, telefonos={})
        assert len(res) == 1

    def test_criterio_alivio_desactivado(self):
        svc = _svc(criterio_mora_activo=False, criterio_pago_tardio_activo=False,
                   criterio_nuevo_activo=False, criterio_alivio_activo=False)
        res = svc.evaluar([_reg(tipo_operacion="NOVA23")], FECHA_CORTE, promedios_mora={}, telefonos={})
        assert len(res) == 0


# ── Lógica OR: cualquier criterio activo selecciona ──────────────────────

class TestLogicaOR:

    def test_solo_c1_true_selecciona(self):
        svc = _svc()
        res = svc.evaluar([_reg()], FECHA_CORTE, promedios_mora={"OP001": 5}, telefonos={})
        assert len(res) == 1
        assert res[0].aplica_gestion is True

    def test_ninguno_true_no_selecciona(self):
        svc = _svc()
        res = svc.evaluar([_reg()], FECHA_CORTE, promedios_mora={"OP001": 0}, telefonos={})
        assert len(res) == 0

    def test_multiples_registros_seleccion_parcial(self):
        registros = [
            _reg("OP001", tipo_operacion="NOVA23"),   # C4 activo
            _reg("OP002", tipo_operacion="CREDITO"),  # ninguno
        ]
        svc = _svc(criterio_mora_activo=False, criterio_pago_tardio_activo=False, criterio_nuevo_activo=False)
        res = svc.evaluar(registros, FECHA_CORTE, promedios_mora={}, telefonos={})
        assert len(res) == 1
        assert res[0].operacion == "OP001"

    def test_telefono_se_asigna_desde_dict(self):
        svc = _svc()
        telefonos = {"1700000001": "0991234567"}
        res = svc.evaluar([_reg()], FECHA_CORTE, promedios_mora={"OP001": 5}, telefonos=telefonos)
        assert res[0].telefono == "0991234567"

    def test_sin_telefono_campo_vacio(self):
        svc = _svc()
        res = svc.evaluar([_reg()], FECHA_CORTE, promedios_mora={"OP001": 5}, telefonos={})
        assert res[0].telefono == ""
