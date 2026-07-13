"""Cliente HTTP para el servicio compartido de notificaciones (:8002)."""

import logging
from pathlib import Path
from typing import Mapping, Optional, Sequence, Union

import httpx

from notificaciones.domain.models.resultado_envio import ResultadoEnvio
from notificaciones.infrastructure.config.settings import NotificacionesSettings

logger = logging.getLogger("notificaciones.api_client")


class NotificacionesApiClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def enviar(
        self,
        id_proceso: str,
        estado: str,
        asunto: str,
        variables: Optional[Mapping[str, str]] = None,
        adjuntos: Optional[Sequence[Union[Path, str]]] = None,
    ) -> ResultadoEnvio:
        payload = {
            "id_proceso": id_proceso,
            "estado": estado,
            "asunto": asunto,
            "variables": dict(variables or {}),
            "adjuntos": [str(p) for p in (adjuntos or [])],
        }
        return self._post("/enviar", payload)

    def notificar_error(
        self,
        id_proceso: str,
        paso: str,
        causa: str,
        proceso_cod: str = "",
        asunto_prefix: str = "[BOT COBRANZA]",
    ) -> ResultadoEnvio:
        payload = {
            "id_proceso": id_proceso,
            "paso": paso,
            "causa": causa,
            "proceso_cod": proceso_cod,
            "asunto_prefix": asunto_prefix,
        }
        return self._post("/notificar-error", payload)

    def _post(self, path: str, payload: dict) -> ResultadoEnvio:
        url = f"{self._base_url}{path}"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return ResultadoEnvio(
                    enviado=bool(data.get("enviado")),
                    destinatarios=list(data.get("destinatarios") or []),
                    omitido_motivo=str(data.get("omitido_motivo") or ""),
                    errores=list(data.get("errores") or []),
                )
        except httpx.HTTPStatusError as exc:
            detalle = exc.response.text[:500] if exc.response is not None else str(exc)
            logger.warning("API notificaciones HTTP %s: %s", exc.response.status_code, detalle)
            return ResultadoEnvio(errores=[f"HTTP {exc.response.status_code}: {detalle}"])
        except Exception as exc:
            logger.warning("No se pudo contactar API de notificaciones (%s): %s", url, exc)
            return ResultadoEnvio(errores=[str(exc)])


def build_notificaciones_api_client(
    settings: Optional[NotificacionesSettings] = None,
) -> NotificacionesApiClient:
    cfg = settings or NotificacionesSettings()
    return NotificacionesApiClient(
        base_url=cfg.api_base_url(),
        timeout=cfg.notificaciones_api_timeout,
    )
