import logging
from pathlib import Path
from typing import Optional

from cobranzas.application.chain.handler import Handler
from cobranzas.application.chain.proceso_context import ProcesoContext
from cobranzas.domain.ports.feriados_calendario_port import FeriadosCalendarioPort
from cobranzas.domain.services.asignacion_calendario import debe_exportar_asignacion
from cobranzas.domain.services.exportar_asignacion_service import ExportarAsignacionService
from cobranzas.infrastructure.config.entregables_mensuales import (
    ruta_asignacion_desde_fecha_archivo,
)

logger = logging.getLogger(__name__)


def _normalizar_operacion(valor: object) -> str:
    """
    Normaliza número de operación para que coincida con los .lis y Recblue.

    Ejemplos:
    - 18645311    -> 0018645311
    - 18645311.0  -> 0018645311
    - 0018645311  -> 0018645311
    """
    texto = str(valor or "").strip()

    if texto.endswith(".0"):
        texto = texto[:-2]

    texto = "".join(ch for ch in texto if ch.isdigit())

    if texto:
        texto = texto.zfill(10)

    return texto


class ExportAsignacionHandler(Handler):
    """Genera ASIGNACION.csv usando únicamente contexto.asignaciones."""

    def __init__(
        self,
        export_service: ExportarAsignacionService,
        feriados_repository: Optional[FeriadosCalendarioPort] = None,
        directorio_destino: Optional[Path] = None,
    ) -> None:
        super().__init__()
        self._export = export_service
        self._feriados = feriados_repository
        self._directorio_destino = directorio_destino

    def _procesar(self, contexto: ProcesoContext) -> ProcesoContext:
        if contexto.es_fin_de_mes:
            logger.info(
                "ASIGNACION.csv omitido | fin de mes | solo se almacena sin asesor"
            )
            return contexto

        if contexto.creditos:
            fecha_corte = contexto.creditos[0].fecha_corte
            if not debe_exportar_asignacion(fecha_corte):
                logger.info(
                    "ASIGNACION.csv omitido | %s | último día del mes | solo historial",
                    fecha_corte.isoformat(),
                )
                return contexto

        if not contexto.asignaciones:
            logger.info("ASIGNACION.csv omitido | sin asignaciones en contexto")
            return contexto

        """
        IMPORTANTE:
        Este mapa NO define cuántas filas salen en ASIGNACION.csv.

        Solo sirve para completar ID_CREDITO Recblue de las operaciones que YA están
        en contexto.asignaciones.

        Antes el riesgo era usar todo el mapa Recblue SQL Server, que puede traer
        miles de CREDITOS activos y generar filas de más.
        """
        ids_recblue = {}

        for credito in contexto.creditos_mora:
            numero_operacion = _normalizar_operacion(credito.id_credito)
            id_recblue = str(credito.id_credito_recblue or "").strip()

            if numero_operacion and id_recblue:
                ids_recblue[numero_operacion] = id_recblue

        ruta = self._resolver_ruta_asignacion(contexto)
        contexto.archivo_asignacion = ruta

        self._export.exportar_csv(
            ruta,
            contexto.asignaciones,
            ids_recblue_por_operacion=ids_recblue,
            solo_nuevas=True,
        )

        logger.info(
            "Entregable ASIGNACION.csv | archivo=%s | asignaciones_contexto=%s | ids_recblue_contexto=%s",
            ruta,
            len(contexto.asignaciones),
            len(ids_recblue),
        )

        return contexto

    def _resolver_ruta_asignacion(self, contexto: ProcesoContext) -> Path:
        if not contexto.creditos or self._directorio_destino is None:
            return contexto.archivo_asignacion

        fecha_archivo = contexto.creditos[0].fecha_corte

        feriados = (
            self._feriados.fechas_vigentes()
            if self._feriados is not None
            else set()
        )

        return ruta_asignacion_desde_fecha_archivo(
            self._directorio_destino,
            fecha_archivo,
            set(feriados),
        )