"""Handler 3: Aplica los 4 criterios de selección preventiva."""

import logging

from preventiva.application.chain.handler import PreventivaHandler
from preventiva.application.chain.preventiva_context import PreventivaContext
from preventiva.domain.services.seleccion_preventiva_service import SeleccionPreventivaService

log = logging.getLogger("preventiva.chain.seleccion")


class SeleccionHandler(PreventivaHandler):

    def __init__(self, servicio: SeleccionPreventivaService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._svc = servicio

    def _procesar(self, ctx: PreventivaContext) -> PreventivaContext:
        ctx.seleccionados = self._svc.evaluar(
            registros=ctx.registros_cadetacaco,
            fecha_corte=ctx.fecha_ejecucion,
            promedios_mora=ctx.promedios_mora,
            telefonos=ctx.telefonos,
            meses_con_mora=ctx.meses_con_mora,
        )
        log.info(
            "Seleccion: %d/%d operaciones califican para gestión preventiva",
            len(ctx.seleccionados),
            len(ctx.registros_cadetacaco),
        )
        return ctx
