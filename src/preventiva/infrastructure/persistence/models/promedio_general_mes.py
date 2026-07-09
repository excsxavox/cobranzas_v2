from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Numeric, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from preventiva.infrastructure.persistence.base import Base


class PromedioGeneralMes(Base):
    __tablename__ = "promedio_general_mes"

    id:                   Mapped[int]            = mapped_column(BigInteger,    primary_key=True, autoincrement=True)
    proceso_cod:          Mapped[str]            = mapped_column(String(14),    ForeignKey("historial_proceso.proceso_cod"), nullable=False)
    dia_corte:            Mapped[Optional[int]]  = mapped_column(Integer,       nullable=True)
    operacion:            Mapped[str]            = mapped_column(String(30),    nullable=False)
    identificacion:       Mapped[Optional[str]]  = mapped_column(String(20),    nullable=True)
    nombre:               Mapped[Optional[str]]  = mapped_column(String(200),   nullable=True)
    telefono:             Mapped[Optional[str]]  = mapped_column(String(30),    nullable=True)
    tipo_operacion:       Mapped[Optional[str]]  = mapped_column(String(100),   nullable=True)
    dia_pago:             Mapped[Optional[int]]  = mapped_column(Integer,       nullable=True)
    valor_cuota:          Mapped[Optional[float]]= mapped_column(Numeric(18,2), nullable=True)
    dias_mora_actual:     Mapped[Optional[int]]  = mapped_column(Integer,       nullable=True)
    promedio_meses:       Mapped[Optional[int]]  = mapped_column(Integer,       nullable=True)
    fecha_desde:          Mapped[Optional[date]] = mapped_column(Date,          nullable=True)
    fecha_hasta:          Mapped[Optional[date]] = mapped_column(Date,          nullable=True)
    criterio_mora:        Mapped[Optional[bool]] = mapped_column(Boolean,       nullable=True, default=False)
    criterio_pago_tardio: Mapped[Optional[bool]] = mapped_column(Boolean,       nullable=True, default=False)
    fecha_concesion:      Mapped[Optional[date]] = mapped_column(Date,          nullable=True)
    antiguedad_meses:     Mapped[Optional[int]]  = mapped_column(Integer,       nullable=True)
    criterio_nuevo:       Mapped[Optional[bool]] = mapped_column(Boolean,       nullable=True, default=False)
    criterio_alivio:      Mapped[Optional[bool]] = mapped_column(Boolean,       nullable=True, default=False)
    aplica_gestion:       Mapped[Optional[str]]  = mapped_column(String(2),     nullable=True)
    saldo_cuenta:         Mapped[Optional[float]]= mapped_column(Numeric(18,2), nullable=True)
    valor_faltante:       Mapped[Optional[float]]= mapped_column(Numeric(18,2), nullable=True)
    cobertura:            Mapped[Optional[str]]  = mapped_column(String(10),    nullable=True)
    fecha_actualiza:      Mapped[datetime]       = mapped_column(DateTime,      nullable=False, default=datetime.utcnow)
