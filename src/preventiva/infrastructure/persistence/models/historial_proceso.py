from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from preventiva.infrastructure.persistence.base import Base


class HistorialProceso(Base):
    __tablename__ = "historial_proceso"

    proceso_cod:    Mapped[str]           = mapped_column(String(14),  primary_key=True)
    fecha_inicio:   Mapped[datetime]      = mapped_column(DateTime,    nullable=False,  default=datetime.utcnow)
    fecha_fin:      Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    estado:         Mapped[str]           = mapped_column(String(10),  nullable=False,  default="EN_CURSO")
    numero_gestion: Mapped[Optional[int]] = mapped_column(Integer,     nullable=True)
    dia_corte:      Mapped[Optional[int]] = mapped_column(Integer,     nullable=True)
    modo:           Mapped[str]           = mapped_column(String(20),  nullable=False,  default="corte")
