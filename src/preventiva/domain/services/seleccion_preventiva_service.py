"""
Servicio de selección de clientes para gestión preventiva (HU GRC-03).

Criterios de inclusión (OR de los 4):
  1. Mora promedio > N días en últimos M meses (camorosico histórico).
  2. Pago tardío recurrente: retraso >= N días de forma consistente en 6 meses.
  3. Crédito nuevo ≤ M meses desde la concesión (SIN validar mora).
  4. Alivio financiero vigente: novación, refinanciamiento o reestructuración
     (SIN validar mora).

Los umbrales son parametrizables (tabla dbo.parametros).
"""

from datetime import date
from typing import Dict, List, Set

from preventiva.domain.models.registro_lis import RegistroCadetacaco, RegistroSeleccion


class SeleccionPreventivaService:

    def __init__(
        self,
        umbral_mora_dias: int = 5,
        numero_meses: int = 6,
        antiguedad_max_meses: int = 6,
        dias_retraso_recurrente: int = 5,
        tipos_alivio: Set[str] | None = None,
    ) -> None:
        self._umbral_mora = umbral_mora_dias
        self._numero_meses = numero_meses
        self._antiguedad_max = antiguedad_max_meses
        self._dias_retraso = dias_retraso_recurrente
        self._tipos_alivio: Set[str] = {t.upper() for t in (tipos_alivio or set())}

    def evaluar(
        self,
        registros: List[RegistroCadetacaco],
        fecha_corte: date,
        promedios_mora: Dict[str, int],
        telefonos: Dict[str, str],
    ) -> List[RegistroSeleccion]:
        """
        Evalúa cada operación contra los 4 criterios y retorna la lista
        de RegistroSeleccion con aplica_gestion=True para las que califican.
        """
        resultados: List[RegistroSeleccion] = []

        for reg in registros:
            sel = RegistroSeleccion(
                operacion=reg.operacion,
                identificacion=reg.identificacion,
                nombre=reg.nombre,
                telefono=telefonos.get(reg.identificacion, ""),
                tipo_operacion=reg.tipo_operacion,
                dia_pago=reg.dia_pago,
                valor_cuota=reg.valor_cuota,
                dias_mora_actual=reg.dias_mora,
                fecha_concesion=reg.fecha_concesion,
            )

            # Criterio 1: mora promedio
            promedio = promedios_mora.get(reg.operacion, 0)
            sel.promedio_meses = promedio
            sel.criterio_mora = promedio >= self._umbral_mora

            # Criterio 2: pago tardío recurrente (camorosico histórico)
            # El cálculo real se delega al HistorialMoraHandler que pasa
            # el promedio ya calculado; criterio_pago_tardio se evalúa
            # comparando días_mora promedio con umbral de retraso recurrente.
            sel.criterio_pago_tardio = promedio >= self._dias_retraso

            # Criterio 3: crédito nuevo ≤ M meses (sin check mora)
            if reg.fecha_concesion:
                delta_meses = (
                    (fecha_corte.year - reg.fecha_concesion.year) * 12
                    + (fecha_corte.month - reg.fecha_concesion.month)
                )
                sel.antiguedad_meses = delta_meses
                sel.criterio_nuevo = delta_meses <= self._antiguedad_max

            # Criterio 4: alivio financiero (sin check mora)
            sel.criterio_alivio = reg.tipo_operacion.upper() in self._tipos_alivio

            # Decisión final
            sel.aplica_gestion = (
                sel.criterio_mora
                or sel.criterio_pago_tardio
                or sel.criterio_nuevo
                or sel.criterio_alivio
            )

            if sel.aplica_gestion:
                resultados.append(sel)

        return resultados
