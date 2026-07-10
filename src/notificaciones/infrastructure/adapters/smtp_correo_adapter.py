"""Adaptador SMTP con soporte de destinatarios CC y adjuntos."""

import logging
import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

from notificaciones.domain.models.mensaje_correo import MensajeCorreo
from notificaciones.domain.ports.correo_port import CorreoPort

logger = logging.getLogger("notificaciones.smtp")


class SmtpCorreoAdapter(CorreoPort):
    def __init__(
        self,
        host: str,
        port: int,
        usuario: Optional[str] = None,
        password: Optional[str] = None,
        remitente: Optional[str] = None,
        usar_tls: bool = True,
        usar_ssl: bool = False,
    ) -> None:
        if not host:
            raise ValueError("SMTP_HOST es obligatorio para enviar correos")
        self._host = host
        self._port = port
        self._usuario = usuario
        self._password = password
        self._remitente = remitente or usuario
        if not self._remitente:
            raise ValueError("SMTP_FROM o SMTP_USER es obligatorio para enviar correos")
        self._usar_tls = usar_tls
        self._usar_ssl = usar_ssl

    def enviar(self, mensaje: MensajeCorreo) -> None:
        if not mensaje.para:
            raise ValueError("Sin destinatarios para el correo")

        email = EmailMessage()
        email["From"] = self._remitente
        email["To"] = ", ".join(mensaje.para)
        if mensaje.cc:
            email["Cc"] = ", ".join(mensaje.cc)
        email["Subject"] = mensaje.asunto
        email.set_content(mensaje.cuerpo)

        for path in mensaje.adjuntos:
            self._agregar_adjunto(email, path)

        destinatarios = list(mensaje.para) + list(mensaje.cc)

        if self._usar_ssl:
            with smtplib.SMTP_SSL(self._host, self._port, timeout=60) as smtp:
                self._autenticar(smtp)
                smtp.send_message(email, to_addrs=destinatarios)
        else:
            with smtplib.SMTP(self._host, self._port, timeout=60) as smtp:
                if self._usar_tls:
                    smtp.starttls()
                self._autenticar(smtp)
                smtp.send_message(email, to_addrs=destinatarios)

        logger.debug(
            "Correo enviado vía %s:%s a %d destinatario(s)",
            self._host,
            self._port,
            len(destinatarios),
        )

    def _agregar_adjunto(self, email: EmailMessage, path: Path) -> None:
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"
        with path.open("rb") as archivo:
            email.add_attachment(
                archivo.read(),
                maintype=maintype,
                subtype=subtype,
                filename=path.name,
            )

    def _autenticar(self, smtp: smtplib.SMTP) -> None:
        if self._usuario and self._password:
            smtp.login(self._usuario, self._password)
