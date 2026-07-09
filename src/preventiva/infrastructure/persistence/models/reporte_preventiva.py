from datetime import date
from typing import Optional

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from preventiva.infrastructure.persistence.base import Base


class ReportePreventiva(Base):
    __tablename__ = "reporte_preventiva"

    id:               Mapped[int]            = mapped_column(BigInteger,    primary_key=True, autoincrement=True)
    proceso_cod:      Mapped[str]            = mapped_column(String(14),    ForeignKey("historial_proceso.proceso_cod"), nullable=False)
    fecha_proceso:    Mapped[date]           = mapped_column(Date,          nullable=False)
    nombre:           Mapped[Optional[str]]  = mapped_column(String(200),   nullable=True)
    cedula:           Mapped[Optional[str]]  = mapped_column(String(20),    nullable=True)
    numero_operacion: Mapped[Optional[str]]  = mapped_column(String(30),    nullable=True)
    dias_mora:        Mapped[Optional[int]]  = mapped_column(Integer,       nullable=True)
    dia_pago:         Mapped[Optional[int]]  = mapped_column(Integer,       nullable=True)
    telefono:         Mapped[Optional[str]]  = mapped_column(String(30),    nullable=True)
    saldo_pendiente:  Mapped[Optional[float]]= mapped_column(Numeric(18,2), nullable=True)
    saldo_cuenta:     Mapped[Optional[float]]= mapped_column(Numeric(18,2), nullable=True)
    numero_gestion:   Mapped[int]            = mapped_column(Integer,       nullable=False)
    id_credito_rb:    Mapped[Optional[str]]  = mapped_column(String(30),    nullable=True)
    dia_corte:        Mapped[Optional[int]]  = mapped_column(Integer,       nullable=True)
