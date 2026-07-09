"""Repositorio de parámetros del sistema (tabla dbo.parametros)."""

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from preventiva.domain.ports.parametros_port import ParametrosPort
from preventiva.infrastructure.persistence.models.parametro import Parametro


class SqlAlchemyParametrosRepository(ParametrosPort):

    def __init__(self, session_factory: sessionmaker) -> None:
        self._sf = session_factory

    def obtener(self, nombre: str, por_defecto: str = "") -> str:
        with self._sf() as session:
            fila = session.scalar(
                select(Parametro)
                .where(Parametro.nombre == nombre, Parametro.activo == True)  # noqa: E712
                .limit(1)
            )
        if fila is None or fila.valor is None:
            return por_defecto
        return fila.valor.strip()
