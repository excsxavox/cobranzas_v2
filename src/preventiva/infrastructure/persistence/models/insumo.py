from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from preventiva.infrastructure.persistence.base import Base


class Insumo(Base):
    __tablename__ = "insumos"

    insumos_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre:     Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    tabla:      Mapped[str] = mapped_column(String(128), nullable=False)
