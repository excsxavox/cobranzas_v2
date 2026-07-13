"""
Handler 7: Persiste en BD y genera reportes Excel según HU GRC-03.

Archivos generados al mes (6 cortes × 3 gestiones):
  - 18 TXT para Isabel          → generados por IsabelHandler (siempre)
  -  6 Excel por corte          → generados aquí en G3 de cada corte
  -  1 Excel mensual consolidado → generado en G3 del último corte del mes

Total: 25 archivos al mes.
"""

import calendar
import logging
from pathlib import Path
from typing import Optional, Set

from preventiva.application.chain.handler import PreventivaHandler
from preventiva.application.chain.preventiva_context import PreventivaContext
from preventiva.domain.ports.reporte_port import ReportePort
from preventiva.infrastructure.adapters.reporte_excel_writer import escribir_reporte_mensual

log = logging.getLogger("preventiva.chain.reporte")


def _es_ultimo_corte_del_mes(
    dia_corte: int,
    cortes_activos: Set[int],
    anio: int,
    mes: int,
) -> bool:
    if not cortes_activos:
        return False
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    cortes_del_mes = {c for c in cortes_activos if c <= ultimo_dia}
    return bool(cortes_del_mes) and dia_corte == max(cortes_del_mes)


class ReporteHandler(PreventivaHandler):

    def __init__(
        self,
        reporte_repo: ReportePort,
        directorio_salida: Path,
        cortes_activos: Optional[Set[int]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._repo = reporte_repo
        self._dir = directorio_salida
        self._cortes_activos: Set[int] = cortes_activos or set()

    def _procesar(self, ctx: PreventivaContext) -> PreventivaContext:
        # Persistir siempre en BD (base para los reportes consolidados)
        self._repo.guardar_gestion(
            registros=ctx.seleccionados,
            proceso_cod=ctx.proceso_cod,
            fecha_proceso=ctx.fecha_ejecucion,
            numero_gestion=ctx.numero_gestion,
            dia_corte=ctx.dia_corte,
        )
        log.info(
            "Gestión %d persistida: %d registros (corte %s)",
            ctx.numero_gestion, len(ctx.seleccionados), ctx.dia_corte,
        )

        # G3: genera el Excel del corte (consolida las 3 gestiones)
        if ctx.numero_gestion == 3:
            ctx.ruta_reporte = self._generar_reporte_corte(ctx)

            # Si es el último corte del mes → genera también el mensual
            if _es_ultimo_corte_del_mes(
                ctx.dia_corte,
                self._cortes_activos,
                ctx.fecha_ejecucion.year,
                ctx.fecha_ejecucion.month,
            ):
                self._generar_reporte_mensual(ctx)

        return ctx

    def _generar_reporte_corte(self, ctx: PreventivaContext) -> Optional[Path]:
        """
        Excel con las 3 gestiones del corte.
        Nombre: REPORTE_PREVENTIVA_CORTE{DD}_{MMAAAA}.xlsx
        """
        filas = self._repo.obtener_por_corte(
            anio=ctx.fecha_ejecucion.year,
            mes=ctx.fecha_ejecucion.month,
            dia_corte=ctx.dia_corte,
        )
        if not filas:
            return None

        ruta_tmp = escribir_reporte_mensual(
            filas_bd=filas,
            directorio=self._dir,
            anio=ctx.fecha_ejecucion.year,
            mes=ctx.fecha_ejecucion.month,
        )
        nombre = (
            f"REPORTE_PREVENTIVA_CORTE{ctx.dia_corte:02d}_"
            f"{ctx.fecha_ejecucion.month:02d}{ctx.fecha_ejecucion.year}.xlsx"
        )
        ruta_final = self._dir / nombre
        ruta_tmp.replace(ruta_final)
        log.info("Reporte corte %d: %s (%d registros)", ctx.dia_corte, nombre, len(filas))
        return ruta_final

    def _generar_reporte_mensual(self, ctx: PreventivaContext) -> None:
        """
        Excel consolidado con todos los cortes del mes.
        Nombre: REPORTE_PREVENTIVA_MENSUAL_{MMAAAA}.xlsx
        (HU línea 277: 'último día de corte con toda la información del mes')
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
        nombre_mensual = (
            f"REPORTE_PREVENTIVA_MENSUAL_"
            f"{ctx.fecha_ejecucion.month:02d}{ctx.fecha_ejecucion.year}.xlsx"
        )
        ruta_mensual = self._dir / nombre_mensual
        ruta.replace(ruta_mensual)
        log.info(
            "Reporte MENSUAL %02d/%d: %s (%d registros, %d cortes)",
            ctx.fecha_ejecucion.month, ctx.fecha_ejecucion.year,
            nombre_mensual, len(filas),
            len({f.dia_corte for f in filas}),
        )
