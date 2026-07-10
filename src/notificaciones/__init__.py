"""
Módulo compartido de notificaciones por correo.

Uso desde otros módulos (cobranzas, preventiva):

    from notificaciones import build_notificacion_service

    svc = build_notificacion_service()
    resultado = svc.enviar(
        id_proceso="general",
        estado="OK",
        asunto="[Preventiva] Proceso OK",
        variables={"proceso_cod": "20260709120000"},
        adjuntos=[Path("resultados/PREVENTIVA_CORTE_09072026.txt")],
    )
"""

from notificaciones.domain.models.resultado_envio import ResultadoEnvio
from notificaciones.domain.services.notificacion_service import NotificacionService
from notificaciones.infrastructure.clients.notificaciones_api_client import (
    NotificacionesApiClient,
    build_notificaciones_api_client,
)
from notificaciones.jobs.container import build_notificacion_service

__all__ = [
    "NotificacionService",
    "NotificacionesApiClient",
    "ResultadoEnvio",
    "build_notificacion_service",
    "build_notificaciones_api_client",
]
