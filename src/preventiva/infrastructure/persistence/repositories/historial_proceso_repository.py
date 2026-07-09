"""Repositorio para historial_proceso, ejecucion_pad y logs_cp."""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from preventiva.infrastructure.persistence.models.historial_proceso import HistorialProceso
from preventiva.infrastructure.persistence.models.ejecucion_pad import EjecucionPad
from preventiva.infrastructure.persistence.models.logs_cp import LogCp


class HistorialProcesoRepository:

    def __init__(self, session_factory: sessionmaker) -> None:
        self._sf = session_factory

    def crear(
        self,
        proceso_cod: str,
        dia_corte: int,
        numero_gestion: int,
        modo: str = "corte",
    ) -> None:
        with self._sf() as session:
            session.add(HistorialProceso(
                proceso_cod=proceso_cod,
                fecha_inicio=datetime.utcnow(),
                estado="EN_CURSO",
                dia_corte=dia_corte,
                numero_gestion=numero_gestion,
                modo=modo,
            ))
            session.commit()

    def cerrar(self, proceso_cod: str, estado: str = "OK") -> None:
        with self._sf() as session:
            hp = session.get(HistorialProceso, proceso_cod)
            if hp:
                hp.fecha_fin = datetime.utcnow()
                hp.estado = estado
                session.commit()

    def registrar_paso(
        self,
        proceso_cod: str,
        paso: str,
        estado: str,
        descripcion: Optional[str] = None,
        total: int = 0,
    ) -> None:
        with self._sf() as session:
            session.add(EjecucionPad(
                proceso_cod=proceso_cod,
                paso_ejecucion=paso,
                estado=estado,
                descripcion=descripcion,
                total_registros=total,
                fecha_registro=datetime.utcnow(),
            ))
            session.commit()

    def log(
        self,
        proceso_cod: str,
        proceso_ejecutado: str,
        estado: str,
        descripcion: Optional[str] = None,
        total: int = 0,
        tiempo_total: Optional[str] = None,
    ) -> None:
        with self._sf() as session:
            session.add(LogCp(
                proceso_cod=proceso_cod,
                proceso_ejecutado=proceso_ejecutado,
                estado=estado,
                descripcion=descripcion,
                total_registros=total,
                tiempo_total=tiempo_total,
                fecha_hora=datetime.utcnow(),
            ))
            session.commit()
