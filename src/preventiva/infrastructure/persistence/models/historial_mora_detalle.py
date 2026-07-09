from datetime import date
from typing import Optional

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from preventiva.infrastructure.persistence.base import Base


class HistorialMoraDetalle(Base):
    __tablename__ = "historial_mora_detalle"

    id:             Mapped[int]           = mapped_column(BigInteger,  primary_key=True, autoincrement=True)
    proceso_cod:    Mapped[str]           = mapped_column(String(14),  ForeignKey("historial_proceso.proceso_cod"), nullable=False)
    operacion:      Mapped[str]           = mapped_column(String(30),  nullable=False)
    identificacion: Mapped[Optional[str]] = mapped_column(String(20),  nullable=True)
    nombre:         Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    fecha_corte:    Mapped[date]          = mapped_column(Date,        nullable=False)
    dias_mora:      Mapped[int]           = mapped_column(Integer,     nullable=False, default=0)
    fuente_archivo: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
