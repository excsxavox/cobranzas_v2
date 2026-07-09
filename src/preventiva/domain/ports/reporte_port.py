"""Puerto de persistencia para el reporte de gestión preventiva."""

from abc import ABC, abstractmethod
from datetime import date
from typing import List, TYPE_CHECKING

from preventiva.domain.models.registro_lis import RegistroSeleccion

if TYPE_CHECKING:
    from preventiva.infrastructure.persistence.models.reporte_preventiva import ReportePreventiva


class ReportePort(ABC):

    @abstractmethod
    def guardar_gestion(
        self,
        registros: List[RegistroSeleccion],
        proceso_cod: str,
        fecha_proceso: date,
        numero_gestion: int,
        dia_corte: int,
    ) -> int:
        """Persiste las gestiones en reporte_preventiva. Retorna filas insertadas."""
        raise NotImplementedError

    @abstractmethod
    def obtener_por_mes(self, anio: int, mes: int) -> "List[ReportePreventiva]":
        """Retorna todos los registros del mes para el reporte mensual."""
        raise NotImplementedError

    @abstractmethod
    def obtener_por_corte(self, anio: int, mes: int, dia_corte: int) -> "List[ReportePreventiva]":
        """Retorna todos los registros de un corte en el mes para el reporte por corte."""
        raise NotImplementedError
