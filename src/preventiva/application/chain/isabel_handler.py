"""Handler 6: Escribe el archivo PREVENTIVA_CORTE_*.txt para Isabel."""

import logging
from pathlib import Path

from preventiva.application.chain.handler import PreventivaHandler
from preventiva.application.chain.preventiva_context import PreventivaContext
from preventiva.infrastructure.adapters.isabel_writer import escribir_isabel

log = logging.getLogger("preventiva.chain.isabel")


class IsabelHandler(PreventivaHandler):

    def __init__(self, directorio_salida: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._dir = directorio_salida

    def _procesar(self, ctx: PreventivaContext) -> PreventivaContext:
        ctx.ruta_isabel = escribir_isabel(
            registros=ctx.seleccionados,
            directorio=self._dir,
            fecha=ctx.fecha_ejecucion,
            numero_gestion=ctx.numero_gestion,
        )
        log.info("Isabel: %s", ctx.ruta_isabel)
        return ctx
