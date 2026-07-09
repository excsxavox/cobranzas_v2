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

        # Ventana de N meses (HU líneas 185-192):
        #   fecha_hasta = fecha_ejecucion  (incluye el archivo de hoy recién guardado)
        #   fecha_desde = mismo día (numero_meses-1) meses atrás
        #   Ejemplo HU: ejecución 5-may-2026 → ventana 5-dic-2025 … 5-may-2026
        #   Conteo: may(0) ← abr(1) ← mar(2) ← feb(3) ← ene(4) ← dic(5) = 5 pasos = 5-dic
        fecha_hasta = ctx.fecha_ejecucion
        anio_d, mes_d = fecha_hasta.year, fecha_hasta.month
        dia_d = fecha_hasta.day
        for _ in range(self._numero_meses - 1):
            mes_d -= 1
            if mes_d == 0:
                mes_d = 12
                anio_d -= 1
        # Ajusta si el mes destino tiene menos días (ej. 31-mar → 28-feb)
        import calendar
        ultimo_dia = calendar.monthrange(anio_d, mes_d)[1]
        fecha_desde = date(anio_d, mes_d, min(dia_d, ultimo_dia))

        operaciones = [r.operacion for r in ctx.registros_cadetacaco]
        ctx.promedios_mora = self._repo.obtener_promedio_por_operacion(
            operaciones, fecha_desde, fecha_hasta
        )

        # Publica la ventana en el contexto para que el API la devuelva
        ctx.ventana_desde = fecha_desde
        ctx.ventana_hasta = fecha_hasta

        log.info(
            "HistorialMora: ventana %s → %s  |  promedios para %d operaciones",
            fecha_desde, fecha_hasta, len(ctx.promedios_mora),
        )
        return ctx
