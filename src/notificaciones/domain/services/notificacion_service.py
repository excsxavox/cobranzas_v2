"""Orquesta catálogo de plantillas, renderizado y envío SMTP."""

import logging
from pathlib import Path
from typing import Mapping, Optional, Sequence, Union

from notificaciones.domain.models.mensaje_correo import MensajeCorreo
from notificaciones.domain.models.resultado_envio import ResultadoEnvio
from notificaciones.domain.ports.catalogo_notificaciones_port import CatalogoNotificacionesPort
from notificaciones.domain.ports.correo_port import CorreoPort
from notificaciones.domain.services.plantilla_renderer import parse_emails, render

logger = logging.getLogger("notificaciones.service")

FALLBACK_ID_PROCESO = "general"


class NotificacionService:
    def __init__(
        self,
        catalogo: CatalogoNotificacionesPort,
        correo: Optional[CorreoPort],
        *,
        smtp_configurado: bool = True,
    ) -> None:
        self._catalogo = catalogo
        self._correo = correo
        self._smtp_configurado = smtp_configurado and correo is not None

    def enviar(
        self,
        id_proceso: str,
        estado: str,
        asunto: str,
        variables: Optional[Mapping[str, str]] = None,
        adjuntos: Optional[Sequence[Union[Path, str]]] = None,
    ) -> ResultadoEnvio:
        resultado = ResultadoEnvio()

        if not self._smtp_configurado:
            resultado.omitido_motivo = "SMTP no configurado"
            logger.warning("Notificación omitida: %s", resultado.omitido_motivo)
            return resultado

        plantilla = self._resolver_plantilla(id_proceso, estado)
        if plantilla is None:
            resultado.omitido_motivo = f"Sin plantilla para {id_proceso}/{estado}"
            logger.warning("Notificación omitida: %s", resultado.omitido_motivo)
            return resultado

        para = parse_emails(plantilla.correo_para)
        cc = parse_emails(plantilla.correo_copia)
        if not para:
            resultado.omitido_motivo = "Sin destinatarios en plantilla"
            logger.warning("Notificación omitida: %s", resultado.omitido_motivo)
            return resultado

        cuerpo = render(plantilla.plantilla_correo, variables)
        paths_adjuntos = self._resolver_adjuntos(adjuntos or [])

        mensaje = MensajeCorreo(
            asunto=asunto,
            cuerpo=cuerpo,
            para=para,
            cc=cc,
            adjuntos=paths_adjuntos,
        )

        try:
            assert self._correo is not None
            self._correo.enviar(mensaje)
            resultado.enviado = True
            resultado.destinatarios = list(dict.fromkeys([*para, *cc]))
            logger.info(
                "Notificación enviada | proceso=%s | estado=%s | destinatarios=%d",
                id_proceso,
                estado,
                len(resultado.destinatarios),
            )
        except Exception as exc:
            resultado.errores.append(str(exc))
            logger.exception("Fallo al enviar notificación")
        return resultado

    def notificar_error(
        self,
        id_proceso: str,
        paso: str,
        causa: str,
        proceso_cod: str = "",
        asunto_prefix: str = "[BOT COBRANZA]",
    ) -> ResultadoEnvio:
        return self.enviar(
            id_proceso=id_proceso,
            estado="Error",
            asunto=f"{asunto_prefix} Error en {paso}",
            variables={"paso": paso, "causa": causa, "proceso_cod": proceso_cod},
        )

    def _resolver_plantilla(self, id_proceso: str, estado: str):
        plantilla = self._catalogo.obtener(id_proceso, estado)
        if plantilla is None and id_proceso != FALLBACK_ID_PROCESO:
            plantilla = self._catalogo.obtener(FALLBACK_ID_PROCESO, estado)
        return plantilla

    def _resolver_adjuntos(self, adjuntos: Sequence[Union[Path, str]]) -> list:
        paths = []
        for item in adjuntos:
            path = Path(item)
            if path.is_file():
                paths.append(path)
            else:
                logger.warning("Adjunto omitido (no existe): %s", path)
        return paths
