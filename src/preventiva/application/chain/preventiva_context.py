"""Contexto compartido entre todos los handlers de la cadena preventiva."""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Set

from preventiva.domain.models.registro_lis import (
    RegistroCadetacaco,
    RegistroCamorosico,
    RegistroAhsaldia,
    RegistroSeleccion,
)


@dataclass
class PreventivaContext:
    # Parámetros de entrada
    proceso_cod: str
    fecha_ejecucion: date
    dia_corte: int
    numero_gestion: int
    modo: str = "corte"

    # Estado del pipeline
    ok: bool = True
    mensaje_error: str = ""

    # Datos leídos de archivos .lis
    registros_cadetacaco: List[RegistroCadetacaco] = field(default_factory=list)
    registros_camorosico: List[RegistroCamorosico] = field(default_factory=list)
    registros_ahsaldia:   List[RegistroAhsaldia]   = field(default_factory=list)

    # Feriados (cargados desde dbo.claves/dbo.catalogo)
    feriados: Set[date] = field(default_factory=set)

    # Resultados intermedios
    promedios_mora:  Dict[str, int]   = field(default_factory=dict)   # {operacion: promedio}
    telefonos:       Dict[str, str]   = field(default_factory=dict)   # {identificacion: telefono}
    saldos:          Dict[str, float] = field(default_factory=dict)   # {identificacion: saldo}
    id_creditos_rb:  Dict[str, str]   = field(default_factory=dict)   # {operacion: id_credito}

    # Registros seleccionados (post-criterios y post-saldo)
    seleccionados: List[RegistroSeleccion] = field(default_factory=list)

    # Archivos generados
    ruta_isabel:  Optional[Path] = None
    ruta_reporte: Optional[Path] = None
