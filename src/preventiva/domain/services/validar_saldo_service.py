"""
Valida si el saldo disponible en cuenta cubre la cuota (HU GRC-03).

Cobertura:
  TOTAL      → saldo_cuenta >= valor_cuota
  PARCIAL    → 0 < saldo_cuenta < valor_cuota  (faltante = valor_cuota - saldo_cuenta)
  SIN_FONDOS → saldo_cuenta <= 0

Regla HU (líneas 97-99): cuando el cliente dispone del saldo necesario para
cubrir el valor TOTAL de la cuota, NO debe ser considerado en la gestión
preventiva. Por eso este servicio devuelve solo los registros que aún requieren
gestión (cobertura PARCIAL o SIN_FONDOS).
"""

from typing import Dict, List

from preventiva.domain.models.registro_lis import RegistroSeleccion


class ValidarSaldoService:

    def __init__(self, excluir_cobertura_total: bool = True) -> None:
        # Parametrizable: permite desactivar la exclusión si el negocio lo pide.
        self._excluir_total = excluir_cobertura_total

    def enriquecer(
        self,
        seleccionados: List[RegistroSeleccion],
        saldos: Dict[str, float],
    ) -> List[RegistroSeleccion]:
        """
        Agrega saldo_cuenta, valor_faltante y cobertura a cada registro y
        excluye los de cobertura TOTAL (HU líneas 97-99).
        `saldos` es un dict {identificacion: saldo_disponible}.
        """
        resultado: List[RegistroSeleccion] = []
        for reg in seleccionados:
            saldo = saldos.get(reg.identificacion, 0.0)
            reg.saldo_cuenta = round(saldo, 2)
            if saldo >= reg.valor_cuota and reg.valor_cuota > 0:
                reg.cobertura = "TOTAL"
                reg.valor_faltante = 0.0
            elif saldo > 0:
                reg.cobertura = "PARCIAL"
                reg.valor_faltante = round(reg.valor_cuota - saldo, 2)
            else:
                reg.cobertura = "SIN_FONDOS"
                reg.valor_faltante = round(reg.valor_cuota, 2)

            # HU: con cobertura TOTAL el cliente sale de la gestión.
            if self._excluir_total and reg.cobertura == "TOTAL":
                continue
            resultado.append(reg)

        return resultado
