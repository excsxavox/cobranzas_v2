"""Repositorio para historial_mora_detalle (6 meses de camorosico)."""

import math
from datetime import date
from typing import Dict, List

from sqlalchemy import delete, func, select
from sqlalchemy.orm import sessionmaker

from preventiva.domain.ports.historial_mora_port import HistorialMoraPort
from preventiva.domain.models.registro_lis import RegistroCamorosico
from preventiva.infrastructure.persistence.models.historial_mora_detalle import HistorialMoraDetalle


class SqlAlchemyHistorialMoraRepository(HistorialMoraPort):

    def __init__(self, session_factory: sessionmaker) -> None:
        self._sf = session_factory

    def guardar_lote(self, registros: List[RegistroCamorosico], proceso_cod: str) -> int:
        if not registros:
            return 0
        with self._sf() as session:
            for r in registros:
                session.add(HistorialMoraDetalle(
                    proceso_cod=proceso_cod,
                    operacion=r.operacion,
                    identificacion=r.identificacion,
                    nombre=r.nombre,
                    fecha_corte=r.fecha_corte,
                    dias_mora=r.dias_mora,
                    fuente_archivo=r.fuente_archivo,
                ))
            session.commit()
        return len(registros)

    def obtener_promedio_por_operacion(
        self,
        operaciones: List[str],
        fecha_desde: date,
        fecha_hasta: date,
    ) -> Dict[str, int]:
        if not operaciones:
            return {}
        with self._sf() as session:
            filas = session.execute(
                select(
                    HistorialMoraDetalle.operacion,
                    func.avg(HistorialMoraDetalle.dias_mora).label("promedio"),
                )
                .where(
                    HistorialMoraDetalle.operacion.in_(operaciones),
                    HistorialMoraDetalle.fecha_corte >= fecha_desde,
                    HistorialMoraDetalle.fecha_corte <= fecha_hasta,
                )
                .group_by(HistorialMoraDetalle.operacion)
            ).all()

        return {
            fila.operacion: math.floor(fila.promedio or 0)
            for fila in filas
        }

    def purgar_anteriores_a(self, fecha_limite: date) -> int:
        with self._sf() as session:
            resultado = session.execute(
                delete(HistorialMoraDetalle)
                .where(HistorialMoraDetalle.fecha_corte < fecha_limite)
            )
            session.commit()
            return int(resultado.rowcount or 0)

    def contar_por_fecha(self, fecha_corte: date) -> int:
        """Cuántos registros existen para la fecha dada (para evitar duplicados en backfill)."""
        with self._sf() as session:
            return int(
                session.execute(
                    select(func.count()).where(
                        HistorialMoraDetalle.fecha_corte == fecha_corte
                    )
                ).scalar() or 0
            )
