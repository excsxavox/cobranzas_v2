"""Puerto de persistencia para el reporte de gestión preventiva."""

from abc import ABC, abstractmethod
from datetime import date
from typing import List

from preventiva.domain.models.registro_lis import RegistroSeleccion


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
