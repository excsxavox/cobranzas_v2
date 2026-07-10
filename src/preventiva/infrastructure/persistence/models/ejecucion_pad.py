from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from preventiva.infrastructure.persistence.base import Base


class EjecucionPad(Base):
    __tablename__ = "ejecucion_pad"

    id:              Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    proceso_cod:     Mapped[str]           = mapped_column(String(14), ForeignKey("historial_proceso.proceso_cod"), nullable=False)
    paso_ejecucion:  Mapped[str]           = mapped_column(String(100), nullable=False)
    estado:          Mapped[str]           = mapped_column(String(10),  nullable=False)
    descripcion:     Mapped[Optional[str]] = mapped_column(String(4000), nullable=True)
    total_registros: Mapped[Optional[int]] = mapped_column(Integer,      nullable=True, default=0)
    fecha_registro:  Mapped[datetime]      = mapped_column(DateTime,     nullable=False, default=datetime.utcnow)
