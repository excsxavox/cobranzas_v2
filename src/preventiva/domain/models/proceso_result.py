"""Resultado global de una ejecución del bot de gestión preventiva."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from preventiva.domain.models.registro_lis import RegistroSeleccion


@dataclass
class ProcesoResult:
    proceso_cod: str
    fecha_inicio: datetime
    dia_corte: int
    numero_gestion: int
    modo: str                          # corte / diario / manual

    seleccionados: List[RegistroSeleccion] = field(default_factory=list)
    total_cadetacaco: int = 0
    total_camorosico: int = 0
    total_seleccionados: int = 0
    total_con_saldo: int = 0
    archivo_isabel: str = ""
    archivo_reporte: str = ""
    estado: str = "EN_CURSO"           # OK / ERROR / EN_CURSO
    mensaje_error: str = ""
