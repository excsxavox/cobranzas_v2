"""Handler 7: Escribe el reporte Excel y persiste en reporte_preventiva."""

import logging
from pathlib import Path

from preventiva.application.chain.handler import PreventivaHandler
from preventiva.application.chain.preventiva_context import PreventivaContext
from preventiva.domain.ports.reporte_port import ReportePort
from preventiva.infrastructure.adapters.reporte_excel_writer import escribir_reporte

log = logging.getLogger("preventiva.chain.reporte")


class ReporteHandler(PreventivaHandler):

    def __init__(
        self,
        reporte_repo: ReportePort,
        directorio_salida: Path,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._repo = reporte_repo
        self._dir = directorio_salida

    def _procesar(self, ctx: PreventivaContext) -> PreventivaContext:
        ctx.ruta_reporte = escribir_reporte(
            registros=ctx.seleccionados,
            directorio=self._dir,
            fecha=ctx.fecha_ejecucion,
            numero_gestion=ctx.numero_gestion,
        )
        self._repo.guardar_gestion(
            registros=ctx.seleccionados,
            proceso_cod=ctx.proceso_cod,
            fecha_proceso=ctx.fecha_ejecucion,
            numero_gestion=ctx.numero_gestion,
            dia_corte=ctx.dia_corte,
        )
        log.info("Reporte: %s  (%d gestiones guardadas)", ctx.ruta_reporte, len(ctx.seleccionados))
        return ctx
