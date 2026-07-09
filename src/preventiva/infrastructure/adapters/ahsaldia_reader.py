"""Lee archivos AHSALDIA .lis con saldo disponible en cuenta."""

import csv
import io
import logging
from pathlib import Path
from typing import Dict, List, Optional

from cobranzas.infrastructure.adapters.parser_comun import (
    leer_lineas_archivo,
    parse_float,
    parse_str,
)

from preventiva.domain.models.registro_lis import RegistroAhsaldia

log = logging.getLogger("preventiva.adapters.ahsaldia")

_COL_DEFAULTS = {
    "identificacion":  "IDENTIFICACIÓN",
    "saldo_disponible": "SALDO DISPONIBLE",
}


def leer_ahsaldia(
    path: Path,
    col_map: Optional[Dict[str, str]] = None,
) -> List[RegistroAhsaldia]:
    cols = {**_COL_DEFAULTS, **(col_map or {})}
    lineas = leer_lineas_archivo(path)

    data_inicio = next(
        (i for i, l in enumerate(lineas) if "\t" in l and cols["identificacion"].lower() in l.lower()),
        None,
    )
    if data_inicio is None:
        log.warning("No se encontró cabecera en %s", path)
        return []

    contenido = "\n".join(lineas[data_inicio:])
    reader = csv.DictReader(io.StringIO(contenido), delimiter="\t")

    resultado: List[RegistroAhsaldia] = []
    for fila in reader:
        identificacion = parse_str(fila.get(cols["identificacion"], ""))
        if not identificacion:
            continue
        resultado.append(RegistroAhsaldia(
            identificacion=identificacion,
            saldo_disponible=parse_float(fila.get(cols["saldo_disponible"], "0")),
        ))

    log.info("%s → %d registros leídos", path.name, len(resultado))
    return resultado


def saldos_por_identificacion(registros: List[RegistroAhsaldia]) -> Dict[str, float]:
    return {r.identificacion: r.saldo_disponible for r in registros}
