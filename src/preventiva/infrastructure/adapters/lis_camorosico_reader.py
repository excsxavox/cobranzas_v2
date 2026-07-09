"""
Lee archivos CAMOROSICO .lis y retorna RegistroCamorosico[].

Reutiliza leer_lineas_archivo, parse_int, parse_str de cobranzas.
El mapeo de cabeceras se resuelve desde dbo.insumos_columnas (parametrizable).
"""

import csv
import io
import logging
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

# Reutilización directa desde carteramora
from cobranzas.infrastructure.adapters.parser_comun import (
    leer_lineas_archivo,
    parse_int,
    parse_str,
)

from preventiva.domain.models.registro_lis import RegistroCamorosico

log = logging.getLogger("preventiva.adapters.camorosico")

# Cabeceras por defecto (sobreescribibles desde dbo.insumos_columnas)
_COL_DEFAULTS = {
    "operacion":      "OPERACIÓN",
    "dias_mora":      "DÍAS ATRASO",
    "identificacion": "IDENTIFICACIÓN",
    "nombre":         "NOMBRE SOCIO",
    "telefono":       "TELÉFONO",
}


def leer_camorosico(
    path: Path,
    fecha_corte: Optional[date] = None,
    col_map: Optional[Dict[str, str]] = None,
) -> List[RegistroCamorosico]:
    """
    Parsea un archivo CAMOROSICO .lis tab-separado.
    `col_map` sobreescribe los nombres de cabecera (de dbo.insumos_columnas).
    """
    cols = {**_COL_DEFAULTS, **(col_map or {})}
    lineas = leer_lineas_archivo(path)

    data_inicio = next(
        (i for i, l in enumerate(lineas) if "\t" in l and cols["operacion"].lower() in l.lower()),
        None,
    )
    if data_inicio is None:
        log.warning("No se encontró cabecera en %s", path)
        return []

    contenido = "\n".join(lineas[data_inicio:])
    reader = csv.DictReader(io.StringIO(contenido), delimiter="\t")

    resultado: List[RegistroCamorosico] = []
    for fila in reader:
        # Normaliza claves (quita espacios y tildes de las cabeceras reales)
        operacion = parse_str(fila.get(cols["operacion"], ""))
        if not operacion or not operacion.isdigit():
            continue
        resultado.append(RegistroCamorosico(
            operacion=operacion,
            identificacion=parse_str(fila.get(cols["identificacion"], "")),
            nombre=parse_str(fila.get(cols["nombre"], "")),
            dias_mora=parse_int(fila.get(cols["dias_mora"], "0")),
            telefono=parse_str(fila.get(cols["telefono"], "")),
            fecha_corte=fecha_corte,
            fuente_archivo=str(path),
        ))

    log.info("%s → %d registros leídos", path.name, len(resultado))
    return resultado
