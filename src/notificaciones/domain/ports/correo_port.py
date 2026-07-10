from typing import Protocol

from notificaciones.domain.models.mensaje_correo import MensajeCorreo


class CorreoPort(Protocol):
    def enviar(self, mensaje: MensajeCorreo) -> None:
        ...
