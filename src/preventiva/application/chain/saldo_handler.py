"""Handler 4: Lee AHSALDIA y valida cobertura de cuota."""

import logging
from datetime import date
from pathlib import Path
from typing import Callable, List

from preventiva.application.chain.handler import PreventivaHandler
from preventiva.application.chain.preventiva_context import PreventivaContext
from preventiva.domain.services.validar_saldo_service import ValidarSaldoService
from preventiva.infrastructure.adapters.ahsaldia_reader import leer_ahsaldia, saldos_por_identificacion

log = logging.getLogger("preventiva.chain.saldo")


class SaldoHandler(PreventivaHandler):

    def __init__(
        self,
        servicio: ValidarSaldoService,
        resolver_ahsaldia: Callable[[date], List[Path]],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._svc = servicio
        self._resolver = resolver_ahsaldia

    def _procesar(self, ctx: PreventivaContext) -> PreventivaContext:
        for path in self._resolver(ctx.fecha_ejecucion):
            ctx.registros_ahsaldia.extend(leer_ahsaldia(path))

        ctx.saldos = saldos_por_identificacion(ctx.registros_ahsaldia)
        ctx.seleccionados = self._svc.enriquecer(ctx.seleccionados, ctx.saldos)

        total_con_saldo = sum(1 for r in ctx.seleccionados if r.saldo_cuenta > 0)
        log.info("Saldo: %d con saldo disponible de %d seleccionados", total_con_saldo, len(ctx.seleccionados))
        return ctx
