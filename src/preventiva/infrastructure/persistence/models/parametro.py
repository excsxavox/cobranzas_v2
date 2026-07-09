from typing import Optional

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from preventiva.infrastructure.persistence.base import Base


class Parametro(Base):
    __tablename__ = "parametros"

    id:          Mapped[int]           = mapped_column(Integer,       primary_key=True, autoincrement=True)
    nombre:      Mapped[str]           = mapped_column(String(100),   nullable=False,   unique=True)
    valor:       Mapped[Optional[str]] = mapped_column(String(1000),  nullable=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(500),   nullable=True)
    activo:      Mapped[bool]          = mapped_column(Boolean,       nullable=False,   default=True)
