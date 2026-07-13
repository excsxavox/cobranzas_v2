from typing import Optional

from sqlalchemy import BigInteger, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from preventiva.infrastructure.persistence.base import Base


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id:               Mapped[int]           = mapped_column(Integer,       primary_key=True, autoincrement=True)
    id_proceso:       Mapped[str]           = mapped_column(String(100),   nullable=False)
    estado:           Mapped[str]           = mapped_column(String(10),    nullable=False)
    correo_para:      Mapped[str]           = mapped_column(String(1000),  nullable=False)
    correo_copia:     Mapped[Optional[str]] = mapped_column(String(1000),  nullable=True)
    plantilla_correo: Mapped[str]           = mapped_column(String(4000),  nullable=False)
    activo:           Mapped[bool]          = mapped_column(Boolean,       nullable=False, default=True)
