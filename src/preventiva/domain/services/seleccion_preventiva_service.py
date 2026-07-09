"""
Servicio de selección de clientes para gestión preventiva (HU GRC-03).

Criterios de inclusión (OR de los 4):
  1. Mora promedio ≥ N días en últimos M meses (camorosico histórico).
  2. Pago tardío RECURRENTE: aparece con mora en ≥ K de los M meses
     (consistencia — HU líneas 63-66 y 176-188).
  3. Crédito nuevo ≤ M meses desde la concesión (SIN validar mora).
  4. Alivio financiero vigente: novación, refinanciamiento o reestructuración
     (SIN validar mora).

Los umbrales son parametrizables (tabla dbo.parametros).
"""

from datetime import date
from typing import Dict, List, Optional, Set

from preventiva.domain.models.registro_lis import RegistroCadetacaco, RegistroSeleccion


class SeleccionPreventivaService:

    def __init__(
        self,
        umbral_mora_dias: int = 5,
        numero_meses: int = 6,
        antiguedad_max_meses: int = 6,
        dias_retraso_recurrente: int = 5,
        meses_consistencia: int = 5,       # C2: mínimo de meses con mora para ser "recurrente"
        tipos_alivio: Optional[Set[str]] = None,
        # Activación/desactivación de cada filtro (parametrizable)
        criterio_mora_activo: bool = True,
        criterio_pago_tardio_activo: bool = True,
        criterio_nuevo_activo: bool = True,
        criterio_alivio_activo: bool = True,
    ) -> None:
        self._umbral_mora = umbral_mora_dias
        self._numero_meses = numero_meses
        self._antiguedad_max = antiguedad_max_meses
        self._dias_retraso = dias_retraso_recurrente
        self._meses_consistencia = meses_consistencia
        self._tipos_alivio: Set[str] = {t.upper() for t in (tipos_alivio or set())}
        self._c1_activo = criterio_mora_activo
        self._c2_activo = criterio_pago_tardio_activo
        self._c3_activo = criterio_nuevo_activo
        self._c4_activo = criterio_alivio_activo

    def evaluar(
        self,
        registros: List[RegistroCadetacaco],
        fecha_corte: date,
        promedios_mora: Dict[str, int],
        telefonos: Dict[str, str],
        meses_con_mora: Optional[Dict[str, int]] = None,
    ) -> List[RegistroSeleccion]:
        """
        Evalúa cada operación contra los 4 criterios y retorna la lista
        de RegistroSeleccion con aplica_gestion=True para las que califican.

        meses_con_mora — dict {operacion: n_meses} calculado por HistorialMoraHandler.
        Si no se provee, C2 usa el promedio como fallback.
        """
        _meses = meses_con_mora or {}
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

            # Criterio 1: mora promedio ≥ N días (HU líneas 60-61 y 176-181)
            promedio = promedios_mora.get(reg.operacion, 0)
            sel.promedio_meses = promedio
            if self._c1_activo:
                sel.criterio_mora = promedio >= self._umbral_mora

            # Criterio 2: pago tardío recurrente — aparece con mora en ≥ K meses
            # (HU líneas 63-66: "de forma consistente en los últimos 6 meses")
            # Fuente: CAMOROSICO histórico (HU líneas 185-188)
            if self._c2_activo:
                meses = _meses.get(reg.operacion, 0)
                sel.criterio_pago_tardio = meses >= self._meses_consistencia

            # Criterio 3: crédito nuevo ≤ M meses (sin check mora)
            if reg.fecha_concesion:
                delta_meses = (
                    (fecha_corte.year - reg.fecha_concesion.year) * 12
                    + (fecha_corte.month - reg.fecha_concesion.month)
                )
                sel.antiguedad_meses = delta_meses
                if self._c3_activo:
                    sel.criterio_nuevo = delta_meses <= self._antiguedad_max

            # Criterio 4: alivio financiero (sin check mora)
            if self._c4_activo:
                sel.criterio_alivio = reg.tipo_operacion.upper() in self._tipos_alivio

            # Decisión final (OR de los 4 criterios)
            sel.aplica_gestion = (
                sel.criterio_mora
                or sel.criterio_pago_tardio
                or sel.criterio_nuevo
                or sel.criterio_alivio
            )

            if sel.aplica_gestion:
                resultados.append(sel)

        return resultados
