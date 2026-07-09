import logging
from typing import Any

from cobranzas.application.chain.pipeline.pipeline_context import PipelineContext
from cobranzas.application.chain.pipeline.pipeline_handler import PipelineHandler
from cobranzas.jobs.sync_asesores_container import build_sincronizar_asesores_use_case

logger = logging.getLogger("cobranzas.pipeline.sync_asesores")


def _obtener_fecha_corte(settings: Any) -> str:
    """
    Obtiene la fecha de corte desde Settings si existe.
    Se usa solo para el correo de error.
    """
    fecha = getattr(settings, "fecha_corte", None)

    if fecha is None:
        return ""

    try:
        if hasattr(fecha, "strftime"):
            return fecha.strftime("%m%d%Y")
        return str(fecha)
    except Exception:
        return str(fecha)


def _notificar_fallo_sync_asesores(
    settings: Any,
    exc: Exception,
) -> None:
    """
    Envía correo cuando falla la sincronización de asesores desde Recblue.

    Importante:
    Si el correo falla, NO se detiene el pipeline.
    """
    try:
        from cobranzas.jobs.notificar_error import notificar_error_pipeline

        fecha_corte = _obtener_fecha_corte(settings)

        notificar_error_pipeline(
            settings,
            origen="Job 0 asesores - conexión Recblue / BDDSICUIOCM01",
            mensajes=[
                "No se pudo sincronizar asesores desde BDDSICUIOCM01.dbo.USUARIOS.",
                "El proceso continuará usando los asesores existentes en BD_Cobranza.dbo.asesores.",
                str(exc),
            ],
            fecha_corte=fecha_corte,
            exc=exc,
        )

        logger.info(
            "Correo enviado por fallo en sincronización de asesores | fecha_corte=%s",
            fecha_corte,
        )

    except Exception as notify_exc:
        logger.exception(
            "No se pudo enviar correo por fallo en sincronización de asesores | "
            "error_original=%s | error_notificacion=%s",
            exc,
            notify_exc,
        )


class SyncAsesoresPipelineHandler(PipelineHandler):
    """
    Job 0: sincronización de asesores.

    Fuente actual:
        BDDSICUIOCM01.dbo.USUARIOS
        WHERE perfil_usuario='NUBGESTOR'
          AND estado_usr='ACTIVO'

    Regla especial:
        Si no se puede conectar a Recblue / BDDSICUIOCM01, el pipeline NO se detiene.
        Se notifica por correo y se continúa usando los asesores ya existentes
        en BD_Cobranza.dbo.asesores.
    """

    def _procesar(self, contexto: PipelineContext) -> PipelineContext:
        logger.info("--- Cadena: Job 0 asesores ---")

        cfg = contexto.settings

        try:
            resultado = build_sincronizar_asesores_use_case(cfg).ejecutar()

        except Exception as exc:
            logger.exception(
                "No se pudo sincronizar asesores desde Recblue / BDDSICUIOCM01. "
                "El proceso continuará con los asesores existentes en BD_Cobranza."
            )

            _notificar_fallo_sync_asesores(cfg, exc)

            contexto.mensajes.append(
                "Advertencia: no se pudo sincronizar asesores desde Recblue / "
                "BDDSICUIOCM01. Se continúa con los asesores existentes en BD_Cobranza."
            )

            # No detener el pipeline.
            contexto.codigo_salida = 0
            contexto.detener = False
            return contexto

        if resultado.errores:
            mensaje = (
                "La sincronización de asesores terminó con errores. "
                "El proceso continuará con los asesores existentes en BD_Cobranza."
            )

            logger.error("%s | errores=%s", mensaje, resultado.errores)

            _notificar_fallo_sync_asesores(
                cfg,
                RuntimeError(" | ".join(resultado.errores)),
            )

            contexto.mensajes.append(mensaje)
            contexto.mensajes.extend(resultado.errores)

            # No detener el pipeline.
            contexto.codigo_salida = 0
            contexto.detener = False
            return contexto

        logger.info(
            "Job 0 OK | creados=%s actualizados=%s sin_cambios=%s",
            resultado.creados,
            resultado.actualizados,
            resultado.sin_cambios,
        )

        return contexto