"""Utilidad central para alertar errores del pipeline vía API de notificaciones."""

import traceback
from typing import Optional, Sequence

from cobranzas.infrastructure.config.settings import Settings
from notificaciones import build_notificaciones_api_client
from notificaciones.domain.models.resultado_envio import ResultadoEnvio


def notificar_error_pipeline(
    settings: Settings,
    origen: str,
    mensajes: Sequence[str],
    *,
    fecha_corte: str = "",
    exc: Optional[BaseException] = None,
) -> ResultadoEnvio:
    """
    Envía alerta de error vía API compartida (:8002) usando catálogo dbo.notificaciones.
    """
    if not settings.notificaciones_errores_habilitado:
        return ResultadoEnvio(omitido_motivo="notificaciones deshabilitadas")

    traceback_text = ""
    if exc is not None:
        traceback_text = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )

    causa_partes = list(mensajes)
    if fecha_corte:
        causa_partes.insert(0, f"Fecha de corte: {fecha_corte}")
    if traceback_text:
        causa_partes.extend(["", "Traza técnica:", traceback_text])
    causa = "\n".join(causa_partes) if causa_partes else "Sin detalle adicional"

    client = build_notificaciones_api_client()
    return client.notificar_error(
        id_proceso="cartera_mora",
        paso=origen,
        causa=causa,
        asunto_prefix=settings.notificaciones_asunto_prefijo,
    )
