"""Repositorio para guardar el reporte definitivo de gestiones preventivas."""

from datetime import date
from typing import List

from sqlalchemy import select, extract
from sqlalchemy.orm import sessionmaker

from preventiva.domain.ports.reporte_port import ReportePort
from preventiva.domain.models.registro_lis import RegistroSeleccion
from preventiva.infrastructure.persistence.models.reporte_preventiva import ReportePreventiva


class SqlAlchemyReporteRepository(ReportePort):

    def __init__(self, session_factory: sessionmaker) -> None:
        self._sf = session_factory

    def guardar_gestion(
        self,
        registros: List[RegistroSeleccion],
        proceso_cod: str,
        fecha_proceso: date,
        numero_gestion: int,
        dia_corte: int,
    ) -> int:
        if not registros:
            return 0
        with self._sf() as session:
            for r in registros:
                session.add(ReportePreventiva(
                    proceso_cod=proceso_cod,
                    fecha_proceso=fecha_proceso,
                    nombre=r.nombre,
                    cedula=r.identificacion,
                    numero_operacion=r.operacion,
                    dias_mora=r.dias_mora_actual,
                    dia_pago=r.dia_pago,
                    telefono=r.telefono,
                    saldo_pendiente=r.valor_faltante,
                    saldo_cuenta=r.saldo_cuenta,
                    numero_gestion=numero_gestion,
                    id_credito_rb=r.id_credito_rb,
                    dia_corte=dia_corte,
                ))
            session.commit()
        return len(registros)

    def obtener_por_mes(self, anio: int, mes: int) -> List[ReportePreventiva]:
        """Retorna todos los registros del mes dado, ordenados por corte y gestión."""
        with self._sf() as session:
            filas = session.scalars(
                select(ReportePreventiva)
                .where(
                    extract("year",  ReportePreventiva.fecha_proceso) == anio,
                    extract("month", ReportePreventiva.fecha_proceso) == mes,
                )
                .order_by(
                    ReportePreventiva.dia_corte,
                    ReportePreventiva.numero_gestion,
                    ReportePreventiva.fecha_proceso,
                )
            ).all()
        return list(filas)

    def obtener_por_corte(self, anio: int, mes: int, dia_corte: int) -> List[ReportePreventiva]:
        """Retorna los registros de un corte específico en el mes."""
        with self._sf() as session:
            filas = session.scalars(
                select(ReportePreventiva)
                .where(
                    extract("year",  ReportePreventiva.fecha_proceso) == anio,
                    extract("month", ReportePreventiva.fecha_proceso) == mes,
                    ReportePreventiva.dia_corte == dia_corte,
                )
                .order_by(
                    ReportePreventiva.numero_gestion,
                    ReportePreventiva.fecha_proceso,
                )
            ).all()
        return list(filas)
