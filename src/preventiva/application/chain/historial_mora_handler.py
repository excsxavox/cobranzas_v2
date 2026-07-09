"""Handler 2: Persiste historial mora y calcula promedios 6 meses."""

import logging
from datetime import date, timedelta

from preventiva.application.chain.handler import PreventivaHandler
from preventiva.application.chain.preventiva_context import PreventivaContext
from preventiva.domain.ports.historial_mora_port import HistorialMoraPort

log = logging.getLogger("preventiva.chain.historial_mora")


class HistorialMoraHandler(PreventivaHandler):
    """
    1. Purga registros más antiguos que el límite de retención (ventana deslizante).
    2. Guarda los registros camorosico del día en historial_mora_detalle.
    3. Consulta el promedio de N meses para cada operación en cadetacaco.
    4. Extrae el diccionario de teléfonos desde camorosico.
    """

    def __init__(
        self,
        historial_repo: HistorialMoraPort,
        numero_meses: int = 6,
        dias_retencion: int = 190,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._repo = historial_repo
        self._numero_meses = numero_meses
        self._dias_retencion = dias_retencion

    def _procesar(self, ctx: PreventivaContext) -> PreventivaContext:
        # Ventana deslizante: elimina lo que supere el límite de retención
        # para no acumular registros basura (HU: mantener solo N días).
        fecha_limite = ctx.fecha_ejecucion - timedelta(days=self._dias_retencion)
        purgados = self._repo.purgar_anteriores_a(fecha_limite)
        if purgados:
            log.info(
                "HistorialMora: %d registros purgados (anteriores a %s)",
                purgados, fecha_limite,
            )

        # Persistir lote del día
        guardados = self._repo.guardar_lote(ctx.registros_camorosico, ctx.proceso_cod)
        log.info("HistorialMora: %d filas guardadas", guardados)

        # Telefonos desde camorosico (último valor por cedula)
        for r in ctx.registros_camorosico:
            if r.telefono:
                ctx.telefonos[r.identificacion] = r.telefono

        # Ventana de 6 meses
        fecha_hasta = ctx.fecha_ejecucion
        anio_desde, mes_desde = fecha_hasta.year, fecha_hasta.month
        for _ in range(self._numero_meses - 1):
            mes_desde -= 1
            if mes_desde == 0:
                mes_desde = 12
                anio_desde -= 1
        fecha_desde = date(anio_desde, mes_desde, 1)

        operaciones = [r.operacion for r in ctx.registros_cadetacaco]
        ctx.promedios_mora = self._repo.obtener_promedio_por_operacion(
            operaciones, fecha_desde, fecha_hasta
        )

        log.info("HistorialMora: promedios calculados para %d operaciones", len(ctx.promedios_mora))
        return ctx
