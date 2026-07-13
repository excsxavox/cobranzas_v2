"""Puerto de lectura de parámetros del sistema (tabla parametros)."""

from abc import ABC, abstractmethod


class ParametrosPort(ABC):

    @abstractmethod
    def obtener(self, nombre: str, por_defecto: str = "") -> str:
        raise NotImplementedError

    def obtener_int(self, nombre: str, por_defecto: int = 0) -> int:
        valor = self.obtener(nombre, str(por_defecto))
        try:
            return int(valor)
        except (ValueError, TypeError):
            return por_defecto

    def obtener_bool(self, nombre: str, por_defecto: bool = False) -> bool:
        valor = self.obtener(nombre, "").strip().lower()
        if valor in ("true", "si", "sí", "1", "yes"):
            return True
        if valor in ("false", "no", "0"):
            return False
        return por_defecto
