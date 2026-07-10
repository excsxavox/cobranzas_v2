"""Consulta plantillas desde dbo.notificaciones (SQL Server) o notificaciones (SQLite)."""

from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from notificaciones.domain.models.plantilla_notificacion import PlantillaNotificacion
from notificaciones.domain.ports.catalogo_notificaciones_port import CatalogoNotificacionesPort


def _nombre_tabla(engine: Engine) -> str:
    if engine.dialect.name == "sqlite":
        return "notificaciones"
    return "dbo.notificaciones"


class SqlCatalogoNotificacionesAdapter(CatalogoNotificacionesPort):
    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def obtener(self, id_proceso: str, estado: str) -> Optional[PlantillaNotificacion]:
        with self._session_factory() as session:
            tabla = _nombre_tabla(session.bind)
            row = session.execute(
                text(
                    f"""
                    SELECT id_proceso, estado, correo_para, correo_copia, plantilla_correo
                    FROM {tabla}
                    WHERE id_proceso = :id_proceso
                      AND estado = :estado
                      AND activo = 1
                    """
                ),
                {"id_proceso": id_proceso, "estado": estado},
            ).fetchone()

        if row is None:
            return None

        return PlantillaNotificacion(
            id_proceso=row[0],
            estado=row[1],
            correo_para=row[2],
            correo_copia=row[3],
            plantilla_correo=row[4],
        )
