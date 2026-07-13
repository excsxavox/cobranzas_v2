"""
FastAPI app del módulo compartido de notificaciones — puerto :8002.

Endpoints:
  POST /enviar           Envía correo según catálogo dbo.notificaciones
  POST /notificar-error  Atajo para plantillas de estado Error
  GET  /health           Liveness check
"""

import logging
from typing import Optional

from fastapi import FastAPI

from notificaciones.api.schemas import (
    EnviarNotificacionRequest,
    HealthResponse,
    NotificarErrorRequest,
    ResultadoEnvioResponse,
)
from notificaciones.domain.models.resultado_envio import ResultadoEnvio
from notificaciones.infrastructure.config.settings import NotificacionesSettings
from notificaciones.jobs.container import build_notificacion_service

log = logging.getLogger("notificaciones.api")


def _to_response(resultado: ResultadoEnvio) -> ResultadoEnvioResponse:
    return ResultadoEnvioResponse(
        enviado=resultado.enviado,
        destinatarios=list(resultado.destinatarios),
        omitido_motivo=resultado.omitido_motivo,
        errores=list(resultado.errores),
    )


def create_app(settings: Optional[NotificacionesSettings] = None) -> FastAPI:
    cfg = settings or NotificacionesSettings()
    svc = build_notificacion_service(settings=cfg)

    app = FastAPI(
        title="Notificaciones API",
        description=(
            "Servicio compartido de correo para cobranzas, preventiva y otros módulos.\n\n"
            "Lee plantillas desde `dbo.notificaciones` y envía vía SMTP."
        ),
        version="1.0.0",
    )

    @app.get("/health", response_model=HealthResponse, tags=["Sistema"])
    def health() -> HealthResponse:
        return HealthResponse(smtp_configurado=cfg.smtp_habilitado())

    @app.post(
        "/enviar",
        response_model=ResultadoEnvioResponse,
        tags=["Notificaciones"],
        summary="Enviar correo según catálogo",
    )
    def enviar(body: EnviarNotificacionRequest) -> ResultadoEnvioResponse:
        resultado = svc.enviar(
            id_proceso=body.id_proceso,
            estado=body.estado,
            asunto=body.asunto,
            variables=body.variables,
            adjuntos=body.adjuntos,
        )
        return _to_response(resultado)

    @app.post(
        "/notificar-error",
        response_model=ResultadoEnvioResponse,
        tags=["Notificaciones"],
        summary="Atajo para notificación de error",
    )
    def notificar_error(body: NotificarErrorRequest) -> ResultadoEnvioResponse:
        resultado = svc.notificar_error(
            id_proceso=body.id_proceso,
            paso=body.paso,
            causa=body.causa,
            proceso_cod=body.proceso_cod,
            asunto_prefix=body.asunto_prefix,
        )
        return _to_response(resultado)

    return app


try:
    app = create_app()
except Exception as _e:
    logging.getLogger("notificaciones.api").error("Error al crear la app: %s", _e)
    raise
