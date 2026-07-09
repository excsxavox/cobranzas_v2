from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from preventiva.infrastructure.persistence.base import Base


class InsumoColumna(Base):
    __tablename__ = "insumos_columnas"

    insumos_columnas_id: Mapped[int]           = mapped_column(Integer,      primary_key=True, autoincrement=True)
    insumos_id:          Mapped[int]           = mapped_column(Integer,      ForeignKey("insumos.insumos_id"), nullable=False)
    columna_insumo:      Mapped[str]           = mapped_column(String(200),  nullable=False)
    columna_tabla:       Mapped[str]           = mapped_column(String(128),  nullable=False)
    tipo_dato:           Mapped[str]           = mapped_column(String(20),   nullable=False)
    longitud_campo:      Mapped[Optional[str]] = mapped_column(String(20),   nullable=True)
    activo:              Mapped[bool]          = mapped_column(Boolean,      nullable=False, default=True)
