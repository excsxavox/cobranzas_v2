"""Handler 1: Lee los archivos CAMOROSICO y CADETACACO del día."""

import logging
from datetime import date
from pathlib import Path
from typing import Callable, List

from preventiva.application.chain.handler import PreventivaHandler
from preventiva.application.chain.preventiva_context import PreventivaContext
from preventiva.infrastructure.adapters.lis_cadetacaco_reader import leer_cadetacaco
from preventiva.infrastructure.adapters.lis_camorosico_reader import leer_camorosico

log = logging.getLogger("preventiva.chain.parse_lis")


class ParseLisHandler(PreventivaHandler):
    """
    Lee los archivos .lis del día.
    - CADETACACO: cartera vigente (criterios de selección y cuota).
    - CAMOROSICO: mora del día (para historial 6 meses).
    Las rutas las resuelve el `resolver` inyectado (permite testing).
    """

    def __init__(
        self,
        resolver_cadetacaco: Callable[[date], List[Path]],
        resolver_camorosico: Callable[[date], List[Path]],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._resolver_cade = resolver_cadetacaco
        self._resolver_camo = resolver_camorosico

    def _procesar(self, ctx: PreventivaContext) -> PreventivaContext:
        rutas_cade = self._resolver_cade(ctx.fecha_ejecucion)
        rutas_camo = self._resolver_camo(ctx.fecha_ejecucion)

        # HU líneas 139-140: si no se encuentran los archivos, se notifica al
        # usuario y se detiene el proceso (se ejecuta de nuevo manualmente).
        faltantes = []
        if not rutas_cade:
            faltantes.append("CADETACACO")
        if not rutas_camo:
            faltantes.append("CAMOROSICO")
        if faltantes:
            ctx.ok = False
            ctx.mensaje_error = (
                "No se encontraron los archivos requeridos: "
                + ", ".join(faltantes)
                + f" para la fecha {ctx.fecha_ejecucion:%d/%m/%Y}. "
                "Regularice los archivos y ejecute el bot manualmente."
            )
            log.error(ctx.mensaje_error)
            return ctx

        for path in rutas_cade:
            ctx.registros_cadetacaco.extend(
                leer_cadetacaco(path, fecha_corte=ctx.fecha_ejecucion)
            )

        for path in rutas_camo:
            ctx.registros_camorosico.extend(
                leer_camorosico(path, fecha_corte=ctx.fecha_ejecucion)
            )

        log.info(
            "ParseLis: cadetacaco=%d  camorosico=%d",
            len(ctx.registros_cadetacaco),
            len(ctx.registros_camorosico),
        )
        return ctx
