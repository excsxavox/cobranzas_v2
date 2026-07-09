"""Repositorio para guardar el reporte definitivo de gestiones preventivas."""

from datetime import date
from typing import List

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
