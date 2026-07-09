"""
Tests del servicio de validación de saldo (HU GRC-03 líneas 83-108).

Reglas cubiertas:
  TOTAL      — saldo >= cuota → NO incluir en gestión (HU líneas 97-99).
  PARCIAL    — 0 < saldo < cuota → incluir, con valor_faltante calculado.
  SIN_FONDOS — saldo <= 0 → incluir con valor_faltante = cuota completa.
  Ejemplo HU — cuota USD 100, saldo USD 70 → faltante USD 30 (PARCIAL).
"""

import pytest

from preventiva.domain.services.validar_saldo_service import ValidarSaldoService
from preventiva.domain.models.registro_lis import RegistroSeleccion


def _sel(identificacion="1700000001", valor_cuota=100.0) -> RegistroSeleccion:
    return RegistroSeleccion(
        operacion="OP001",
        identificacion=identificacion,
        nombre="TEST",
        telefono="0999999999",
        tipo_operacion="CREDITO",
        dia_pago=5,
        valor_cuota=valor_cuota,
        dias_mora_actual=0,
        fecha_concesion=None,
    )


class TestValidarSaldoService:

    def test_cobertura_total_excluye_cliente(self):
        """HU líneas 97-99: saldo suficiente → NO incluir."""
        svc = ValidarSaldoService(excluir_cobertura_total=True)
        reg = _sel(valor_cuota=100.0)
        result = svc.enriquecer([reg], {"1700000001": 100.0})
        assert len(result) == 0

    def test_cobertura_total_saldo_mayor_excluye(self):
        """Saldo mayor a la cuota también es cobertura TOTAL."""
        svc = ValidarSaldoService()
        reg = _sel(valor_cuota=100.0)
        result = svc.enriquecer([reg], {"1700000001": 150.0})
        assert len(result) == 0

    def test_cobertura_parcial_ejemplo_hu(self):
        """HU ejemplo: cuota 100, saldo 70 → faltante 30, PARCIAL."""
        svc = ValidarSaldoService()
        reg = _sel(valor_cuota=100.0)
        result = svc.enriquecer([reg], {"1700000001": 70.0})
        assert len(result) == 1
        assert result[0].cobertura == "PARCIAL"
        assert result[0].saldo_cuenta == 70.0
        assert result[0].valor_faltante == 30.0

    def test_sin_fondos_incluye_faltante_igual_cuota(self):
        """Saldo 0 → SIN_FONDOS, faltante = valor completo de cuota."""
        svc = ValidarSaldoService()
        reg = _sel(valor_cuota=100.0)
        result = svc.enriquecer([reg], {"1700000001": 0.0})
        assert len(result) == 1
        assert result[0].cobertura == "SIN_FONDOS"
        assert result[0].valor_faltante == 100.0

    def test_sin_fondos_saldo_negativo(self):
        svc = ValidarSaldoService()
        reg = _sel(valor_cuota=100.0)
        result = svc.enriquecer([reg], {"1700000001": -5.0})
        assert result[0].cobertura == "SIN_FONDOS"

    def test_identificacion_no_encontrada_usa_saldo_cero(self):
        """Si la cédula no está en el archivo AHSALDIA → saldo = 0."""
        svc = ValidarSaldoService()
        reg = _sel(identificacion="9999999999", valor_cuota=100.0)
        result = svc.enriquecer([reg], {})
        assert result[0].saldo_cuenta == 0.0
        assert result[0].cobertura == "SIN_FONDOS"

    def test_excluir_cobertura_total_desactivado_incluye_todos(self):
        """Con excluir_cobertura_total=False, incluso los de cobertura TOTAL pasan."""
        svc = ValidarSaldoService(excluir_cobertura_total=False)
        reg = _sel(valor_cuota=100.0)
        result = svc.enriquecer([reg], {"1700000001": 200.0})
        assert len(result) == 1
        assert result[0].cobertura == "TOTAL"

    def test_multiples_registros_mezcla(self):
        registros = [
            _sel("1111111111", 100.0),  # PARCIAL
            _sel("2222222222", 100.0),  # TOTAL → excluir
            _sel("3333333333", 100.0),  # SIN_FONDOS
        ]
        saldos = {
            "1111111111": 60.0,
            "2222222222": 100.0,
            "3333333333": 0.0,
        }
        svc = ValidarSaldoService()
        result = svc.enriquecer(registros, saldos)
        assert len(result) == 2
        coberturas = {r.identificacion: r.cobertura for r in result}
        assert coberturas["1111111111"] == "PARCIAL"
        assert coberturas["3333333333"] == "SIN_FONDOS"

    def test_redondeo_valor_faltante(self):
        """El valor faltante se redondea a 2 decimales."""
        svc = ValidarSaldoService()
        reg = _sel(valor_cuota=100.0)
        result = svc.enriquecer([reg], {"1700000001": 33.333})
        assert result[0].valor_faltante == round(100.0 - 33.333, 2)
