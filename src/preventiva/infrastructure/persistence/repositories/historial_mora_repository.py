"""Repositorio para historial_mora_detalle (6 meses de camorosico)."""

import math
from datetime import date
from typing import Dict, List

from sqlalchemy import delete, func, select
from sqlalchemy.orm import sessionmaker

from preventiva.domain.ports.historial_mora_port import HistorialMoraPort
from preventiva.domain.models.registro_lis import RegistroCamorosico
from preventiva.infrastructure.persistence.models.historial_mora_detalle import HistorialMoraDetalle

# SQLite acepta máximo 999 variables por consulta; usamos 900 para margen seguro.
_CHUNK = 900


def _chunks(lst: List, n: int):
    for i in range(0, len(lst), n):
        yield lst[i: i + n]


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

        # Acumuladores para calcular el promedio ponderado en Python
        suma: Dict[str, float] = {}
        conteo: Dict[str, int] = {}

        with self._sf() as session:
            for chunk in _chunks(operaciones, _CHUNK):
                filas = session.execute(
                    select(
                        HistorialMoraDetalle.operacion,
                        func.avg(HistorialMoraDetalle.dias_mora).label("promedio"),
                        func.count(HistorialMoraDetalle.id).label("cnt"),
                    )
                    .where(
                        HistorialMoraDetalle.operacion.in_(chunk),
                        HistorialMoraDetalle.fecha_corte >= fecha_desde,
                        HistorialMoraDetalle.fecha_corte <= fecha_hasta,
                    )
                    .group_by(HistorialMoraDetalle.operacion)
                ).all()

                for fila in filas:
                    cnt = int(fila.cnt or 1)
                    suma[fila.operacion] = suma.get(fila.operacion, 0.0) + (fila.promedio or 0) * cnt
                    conteo[fila.operacion] = conteo.get(fila.operacion, 0) + cnt

        return {
            op: math.floor(suma[op] / conteo[op]) if conteo[op] else 0
            for op in suma
        }

    def purgar_anteriores_a(self, fecha_limite: date) -> int:
        with self._sf() as session:
            resultado = session.execute(
                delete(HistorialMoraDetalle)
                .where(HistorialMoraDetalle.fecha_corte < fecha_limite)
            )
            session.commit()
            return int(resultado.rowcount or 0)

    def obtener_meses_con_mora_por_operacion(
        self,
        operaciones: List[str],
        fecha_desde: date,
        fecha_hasta: date,
        dias_mora_minimo: int = 1,
    ) -> Dict[str, int]:
        """
        Para C2: cuenta cuántos meses distintos aparece cada operación
        con dias_mora >= dias_mora_minimo dentro de la ventana.
        Procesa en Python para evitar incompatibilidades entre SQLite y SQL Server.
        """
        if not operaciones:
            return {}

        # {operacion: set(año-mes)}
        meses_por_op: Dict[str, set] = {}

        with self._sf() as session:
            for chunk in _chunks(operaciones, _CHUNK):
                filas = session.execute(
                    select(
                        HistorialMoraDetalle.operacion,
                        HistorialMoraDetalle.fecha_corte,
                    )
                    .where(
                        HistorialMoraDetalle.operacion.in_(chunk),
                        HistorialMoraDetalle.fecha_corte >= fecha_desde,
                        HistorialMoraDetalle.fecha_corte <= fecha_hasta,
                        HistorialMoraDetalle.dias_mora >= dias_mora_minimo,
                    )
                ).all()

                for fila in filas:
                    fc: date = fila.fecha_corte
                    # fecha_corte puede llegar como string desde SQLite
                    if isinstance(fc, str):
                        from datetime import datetime as _dt
                        fc = _dt.strptime(fc[:10], "%Y-%m-%d").date()
                    clave = f"{fc.year}-{fc.month:02d}"
                    meses_por_op.setdefault(fila.operacion, set()).add(clave)

        return {op: len(meses) for op, meses in meses_por_op.items()}

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
