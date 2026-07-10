"""Modelo ORM mínimo para dbo.notificaciones (uso opcional en init/test)."""

from typing import Optional

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from notificaciones.infrastructure.persistence.base import Base


class NotificacionCatalogo(Base):
    __tablename__ = "notificaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proceso: Mapped[str] = mapped_column(String(100), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False)
    correo_para: Mapped[str] = mapped_column(String(1000), nullable=False)
    correo_copia: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    plantilla_correo: Mapped[str] = mapped_column(String(4000), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
