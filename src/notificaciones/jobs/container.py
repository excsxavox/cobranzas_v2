"""Composition root del módulo de notificaciones."""

from typing import Optional

from sqlalchemy.orm import sessionmaker

from cobranzas.infrastructure.config.database_url import resolver_database_url
from cobranzas.infrastructure.config.settings import Settings as CobranzasSettings
from cobranzas.infrastructure.persistence.session import get_engine, get_session_factory
from notificaciones.domain.services.notificacion_service import NotificacionService
from notificaciones.infrastructure.adapters.smtp_correo_adapter import SmtpCorreoAdapter
from notificaciones.infrastructure.adapters.sql_catalogo_notificaciones_adapter import (
    SqlCatalogoNotificacionesAdapter,
)
from notificaciones.infrastructure.config.settings import NotificacionesSettings


def build_notificacion_service(
    session_factory: Optional[sessionmaker] = None,
    settings: Optional[NotificacionesSettings] = None,
    cobranzas_settings: Optional[CobranzasSettings] = None,
) -> NotificacionService:
    """
    Construye NotificacionService con catálogo SQL y SMTP.

    Si no se pasa session_factory, usa DATABASE_URL del .env vía cobranzas.
    """
    cfg = settings or NotificacionesSettings()
    sf = session_factory

    if sf is None:
        cobranzas_cfg = cobranzas_settings or CobranzasSettings()
        engine = get_engine(resolver_database_url(cobranzas_cfg))
        sf = get_session_factory(engine)

    catalogo = SqlCatalogoNotificacionesAdapter(sf)
    correo = None
    smtp_ok = cfg.smtp_habilitado()

    if smtp_ok:
        correo = SmtpCorreoAdapter(
            host=cfg.smtp_host or "",
            port=cfg.smtp_port,
            usuario=cfg.smtp_user,
            password=cfg.smtp_password,
            remitente=cfg.smtp_from,
            usar_tls=cfg.smtp_use_tls,
            usar_ssl=cfg.smtp_use_ssl,
        )

    return NotificacionService(catalogo, correo, smtp_configurado=smtp_ok)
