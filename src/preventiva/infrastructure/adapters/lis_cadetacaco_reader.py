"""
Lee archivos CADETACACO .lis y retorna RegistroCadetacaco[].

Reutiliza leer_lineas_archivo y helpers de parseo de cobranzas.
"""

import csv
import io
import logging
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from cobranzas.infrastructure.adapters.parser_comun import (
    leer_lineas_archivo,
    parse_float,
    parse_int,
    parse_str,
)
from cobranzas.domain.services.dias_habiles_service import parse_fecha_cadetacaco

from preventiva.domain.models.registro_lis import RegistroCadetacaco

log = logging.getLogger("preventiva.adapters.cadetacaco")

_COL_DEFAULTS = {
    "operacion":       "OPERACIÓN",
    "identificacion":  "IDENTIFICACIÓN",
    "nombre":          "NOMBRE SOCIO",
    "tipo_operacion":  "TIPO DE OPERACIÓN",
    "dia_pago":        "DIA DE PAGO",
    "valor_cuota":     "VALOR CUOTA",
    "dias_mora":       "DÍAS MORA",
    "fecha_concesion": "FECHA CONCESIÓN",
}


def leer_cadetacaco(
    path: Path,
    fecha_corte: Optional[date] = None,
    col_map: Optional[Dict[str, str]] = None,
) -> List[RegistroCadetacaco]:
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

    resultado: List[RegistroCadetacaco] = []
    for fila in reader:
        operacion = parse_str(fila.get(cols["operacion"], ""))
        if not operacion or not operacion.isdigit():
            continue
        resultado.append(RegistroCadetacaco(
            operacion=operacion,
            identificacion=parse_str(fila.get(cols["identificacion"], "")),
            nombre=parse_str(fila.get(cols["nombre"], "")),
            tipo_operacion=parse_str(fila.get(cols["tipo_operacion"], "")),
            dia_pago=parse_int(fila.get(cols["dia_pago"], "0")),
            valor_cuota=parse_float(fila.get(cols["valor_cuota"], "0")),
            dias_mora=parse_int(fila.get(cols["dias_mora"], "0")),
            fecha_concesion=parse_fecha_cadetacaco(fila.get(cols["fecha_concesion"], "")),
            fecha_corte=fecha_corte,
        ))

    log.info("%s → %d registros leídos", path.name, len(resultado))
    return resultado
