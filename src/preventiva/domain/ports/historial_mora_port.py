"""Puerto de persistencia para el historial de mora de 6 meses."""

from abc import ABC, abstractmethod
from datetime import date
from typing import Dict, List

from preventiva.domain.models.registro_lis import RegistroCamorosico


class HistorialMoraPort(ABC):

    @abstractmethod
    def guardar_lote(self, registros: List[RegistroCamorosico], proceso_cod: str) -> int:
        """Persiste un lote de registros de mora histórica. Retorna filas insertadas."""
        raise NotImplementedError

    @abstractmethod
    def obtener_promedio_por_operacion(
        self,
        operaciones: List[str],
        fecha_desde: date,
        fecha_hasta: date,
    ) -> Dict[str, int]:
        """
        Promedio de días de mora por operación en la ventana [fecha_desde, fecha_hasta].
        Retorna {operacion: floor(promedio)}.
        """
        raise NotImplementedError

    @abstractmethod
    def obtener_meses_con_mora_por_operacion(
        self,
        operaciones: List[str],
        fecha_desde: date,
        fecha_hasta: date,
        dias_mora_minimo: int = 1,
    ) -> Dict[str, int]:
        """
        Cuántos meses distintos aparece cada operación con dias_mora >= dias_mora_minimo.
        Retorna {operacion: cantidad_meses}. Usado para Criterio 2 (consistencia).
        """
        raise NotImplementedError

    @abstractmethod
    def purgar_anteriores_a(self, fecha_limite: date) -> int:
        """
        Elimina los registros con fecha_corte anterior a `fecha_limite`
        (ventana deslizante). Retorna la cantidad de filas eliminadas.
        """
        raise NotImplementedError
