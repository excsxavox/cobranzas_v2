"""
Lee archivos CAMOROSICO .lis y retorna RegistroCamorosico[].

Usa normalizar_encabezados de carteramora (snake_case) para ser robusto
ante cambios de encoding, acentos o versiones del core COBIS.
"""

import logging
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from cobranzas.infrastructure.adapters.parser_comun import (
    leer_lineas_archivo,
    parse_int,
    parse_str,
)
from cobranzas.domain.schemas.tab_schema import normalizar_encabezados

from preventiva.domain.models.registro_lis import RegistroCamorosico

log = logging.getLogger("preventiva.adapters.camorosico")

_CLAVES_OPERACION     = ("operacion", "no_operacion", "numero_operacion")
_CLAVES_MORA          = ("dias_atraso", "dias_mora", "d_as_atraso", "d_as_mora")
_CLAVES_IDENTIFICACION= ("identificacion", "cedula", "no_cedula")
_CLAVES_NOMBRE        = ("nombre_socio", "nombre", "cliente")
_CLAVES_TELEFONO      = ("telefono", "tel_fono", "celular", "telefono_cel")


def _primera(fila: Dict[str, str], claves: tuple, default: str = "") -> str:
    for k in claves:
        if k in fila:
            return fila[k]
    return default


def leer_camorosico(
    path: Path,
    fecha_corte: Optional[date] = None,
    col_map: Optional[Dict[str, str]] = None,
) -> List[RegistroCamorosico]:
    lineas = leer_lineas_archivo(path)

    header_idx = next(
        (i for i, l in enumerate(lineas) if "\t" in l and l.strip()),
        None,
    )
    if header_idx is None:
        log.warning("Sin cabecera TAB en %s", path.name)
        return []

    cab_originales = lineas[header_idx].split("\t")
    cab_norm = normalizar_encabezados(cab_originales)
    log.debug("Cabeceras normalizadas %s: %s", path.name, cab_norm)

    cm = col_map or {}
    resultado: List[RegistroCamorosico] = []

    for linea in lineas[header_idx + 1:]:
        if not linea.strip():
            continue
        valores = linea.split("\t")
        if len(valores) < len(cab_norm):
            valores += [""] * (len(cab_norm) - len(valores))
        fila = dict(zip(cab_norm, valores))

        operacion = parse_str(_primera(fila, (cm.get("operacion"),) if cm.get("operacion") else _CLAVES_OPERACION))
        if not operacion or not operacion.strip().isdigit():
            continue

        resultado.append(RegistroCamorosico(
            operacion=operacion,
            identificacion=parse_str(_primera(fila, (cm.get("identificacion"),) if cm.get("identificacion") else _CLAVES_IDENTIFICACION)),
            nombre=parse_str(_primera(fila, (cm.get("nombre"),) if cm.get("nombre") else _CLAVES_NOMBRE)),
            dias_mora=parse_int(_primera(fila, (cm.get("dias_mora"),) if cm.get("dias_mora") else _CLAVES_MORA)),
            telefono=parse_str(_primera(fila, (cm.get("telefono"),) if cm.get("telefono") else _CLAVES_TELEFONO)),
            fecha_corte=fecha_corte,
            fuente_archivo=str(path),
        ))

    log.info("%s → %d registros leídos", path.name, len(resultado))
    return resultado
