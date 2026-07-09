"""
Handler 7: Escribe el reporte Excel y persiste en reporte_preventiva.

Según HU líneas 275-284:
  - Genera reporte por ejecución (cada gestión del día).
  - Cuando es la gestión 3 (día del corte), genera también el reporte
    consolidado del corte (las 3 gestiones juntas).
  - Si además es el último corte activo del mes, genera el reporte
    mensual consolidado con todos los cortes del mes.
"""

import calendar
import logging
from pathlib import Path
from typing import Set

from preventiva.application.chain.handler import PreventivaHandler
from preventiva.application.chain.preventiva_context import PreventivaContext
from preventiva.domain.ports.reporte_port import ReportePort
from preventiva.infrastructure.adapters.reporte_excel_writer import (
    escribir_reporte,
    escribir_reporte_mensual,
)

log = logging.getLogger("preventiva.chain.reporte")


def _es_ultimo_corte_del_mes(
    dia_corte: int,
    cortes_activos: Set[int],
    anio: int,
    mes: int,
) -> bool:
    """
    Retorna True si dia_corte es el último corte del mes (el de mayor valor
    que cae dentro del mes).
    """
    if not cortes_activos:
        return False
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    cortes_del_mes = {c for c in cortes_activos if c <= ultimo_dia}
    return cortes_del_mes and dia_corte == max(cortes_del_mes)


class ReporteHandler(PreventivaHandler):

    def __init__(
        self,
        reporte_repo: ReportePort,
        directorio_salida: Path,
        cortes_activos: Set[int] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._repo = reporte_repo
        self._dir = directorio_salida
        self._cortes_activos: Set[int] = cortes_activos or set()

    def _procesar(self, ctx: PreventivaContext) -> PreventivaContext:
        # 1. Reporte de la ejecución actual (una gestión)
        ctx.ruta_reporte = escribir_reporte(
            registros=ctx.seleccionados,
            directorio=self._dir,
            fecha=ctx.fecha_ejecucion,
            numero_gestion=ctx.numero_gestion,
        )

        # 2. Persistir en BD
        self._repo.guardar_gestion(
            registros=ctx.seleccionados,
            proceso_cod=ctx.proceso_cod,
            fecha_proceso=ctx.fecha_ejecucion,
            numero_gestion=ctx.numero_gestion,
            dia_corte=ctx.dia_corte,
        )
        log.info("Reporte: %s  (%d registros)", ctx.ruta_reporte.name, len(ctx.seleccionados))

        # 3. Al completar la gestión 3 del corte → reporte consolidado del corte
        if ctx.numero_gestion == 3:
            self._generar_reporte_corte(ctx)

            # 4. Si además es el último corte del mes → reporte mensual completo
            if _es_ultimo_corte_del_mes(
                ctx.dia_corte,
                self._cortes_activos,
                ctx.fecha_ejecucion.year,
                ctx.fecha_ejecucion.month,
            ):
                self._generar_reporte_mensual(ctx)

        return ctx

    def _generar_reporte_corte(self, ctx: PreventivaContext) -> None:
        """Consolida las 3 gestiones del corte en un único Excel."""
        filas = self._repo.obtener_por_corte(
            anio=ctx.fecha_ejecucion.year,
            mes=ctx.fecha_ejecucion.month,
            dia_corte=ctx.dia_corte,
        )
        if not filas:
            return
        ruta = escribir_reporte_mensual(
            filas_bd=filas,
            directorio=self._dir,
            anio=ctx.fecha_ejecucion.year,
            mes=ctx.fecha_ejecucion.month,
        )
        # Sobreescribe con nombre específico por corte
        nombre_corte = (
            f"REPORTE_PREVENTIVA_CORTE{ctx.dia_corte:02d}_"
            f"{ctx.fecha_ejecucion.month:02d}{ctx.fecha_ejecucion.year}.xlsx"
        )
        ruta_corte = self._dir / nombre_corte
        ruta.rename(ruta_corte)
        log.info(
            "Reporte corte %d: %s (%d registros)",
            ctx.dia_corte, ruta_corte.name, len(filas),
        )

    def _generar_reporte_mensual(self, ctx: PreventivaContext) -> None:
        """
        Reporte mensual consolidado con todos los cortes del mes
        (HU líneas 277-284: 'último día de corte con toda la información del mes').
        """
        filas = self._repo.obtener_por_mes(
            anio=ctx.fecha_ejecucion.year,
            mes=ctx.fecha_ejecucion.month,
        )
        if not filas:
            return
        ruta = escribir_reporte_mensual(
            filas_bd=filas,
            directorio=self._dir,
            anio=ctx.fecha_ejecucion.year,
            mes=ctx.fecha_ejecucion.month,
        )
        log.info(
            "Reporte MENSUAL %02d/%d: %s (%d registros, %d cortes)",
            ctx.fecha_ejecucion.month,
            ctx.fecha_ejecucion.year,
            ruta.name,
            len(filas),
            len({f.dia_corte for f in filas}),
        )
