"""
Lee archivos CADETACACO .lis y retorna RegistroCadetacaco[].

Reutiliza leer_lineas_archivo y normalizar_encabezados de carteramora.
Las cabeceras se normalizan a snake_case (igual que tab_lis_staging_reader)
para ser robustos ante cambios de encoding, acentos o versiones del core.

Mapeo normalizado de columnas:
  "OPERACIÓN"       → "operacion"
  "IDENTIFICACIÓN"  → "identificacion"
  "NOMBRE SOCIO"    → "nombre_socio"
  "TIPO DE OPERACIÓN"→ "tipo_de_operacion"
  "DIA DE PAGO"     → "dia_de_pago"
  "VALOR CUOTA"     → "valor_cuota"
  "DÍAS MORA"       → "dias_mora"
  "FECHA CONCESIÓN" → "fecha_concesion"
"""

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
from cobranzas.domain.schemas.tab_schema import normalizar_encabezados
from cobranzas.domain.services.dias_habiles_service import parse_fecha_cadetacaco

from preventiva.domain.models.registro_lis import RegistroCadetacaco

log = logging.getLogger("preventiva.adapters.cadetacaco")

# Claves normalizadas (snake_case) para las columnas requeridas.
# Si el core cambia el nombre de columna, añadir el nuevo nombre normalizado aquí
# o registrar la sobreescritura en dbo.parametros (col_cade_*).
_CLAVES_OPERACION     = ("operacion", "no_operacion", "numero_operacion")
_CLAVES_IDENTIFICACION= ("identificacion", "cedula", "no_cedula")
_CLAVES_NOMBRE        = ("nombre_socio", "nombre", "cliente")
_CLAVES_TIPO          = ("tipo_oper", "tipo_de_operacion", "tipo_operacion", "tipo_oper_")
_CLAVES_DIA_PAGO      = ("dia_de_pago", "dia_pago", "d_a_de_pago")
_CLAVES_CUOTA         = ("valor_cuota", "valor_de_cuota", "cuota")
_CLAVES_MORA          = ("dias_mora", "d_as_mora", "dias_de_mora")
_CLAVES_CONCESION     = ("fecha_concesion", "fecha_de_concesion", "fec_concesion", "fecha_concesi_n")


def _primera(fila: Dict[str, str], claves: tuple, default: str = "") -> str:
    for k in claves:
        if k in fila:
            return fila[k]
    return default


def leer_cadetacaco(
    path: Path,
    fecha_corte: Optional[date] = None,
    col_map: Optional[Dict[str, str]] = None,
) -> List[RegistroCadetacaco]:
    """
    col_map permite sobreescribir los nombres normalizados esperados.
    Ej: {"operacion": "no_operacion_2"} si el core genera columnas duplicadas.
    """
    lineas = leer_lineas_archivo(path)

    # Buscar la línea de cabecera: primera con tab que tenga columnas útiles
    header_idx = next(
        (i for i, l in enumerate(lineas) if "\t" in l and l.strip()),
        None,
    )
    if header_idx is None:
        log.warning("Sin cabecera TAB en %s", path.name)
        return []

    # Normalizar cabeceras a snake_case (igual que carteramora)
    cab_originales = lineas[header_idx].split("\t")
    cab_norm = normalizar_encabezados(cab_originales)
    log.debug("Cabeceras normalizadas %s: %s", path.name, cab_norm)

    resultado: List[RegistroCadetacaco] = []
    for linea in lineas[header_idx + 1:]:
        if not linea.strip():
            continue
        valores = linea.split("\t")
        if len(valores) < len(cab_norm):
            valores += [""] * (len(cab_norm) - len(valores))
        fila = dict(zip(cab_norm, valores))

        # Si se provee col_map, sobreescribe las claves de búsqueda
        cm = col_map or {}
        operacion = parse_str(_primera(fila, (cm.get("operacion"),) if cm.get("operacion") else _CLAVES_OPERACION))
        if not operacion or not operacion.strip().isdigit():
            continue

        resultado.append(RegistroCadetacaco(
            operacion=operacion,
            identificacion=parse_str(_primera(fila, (cm.get("identificacion"),) if cm.get("identificacion") else _CLAVES_IDENTIFICACION)),
            nombre=parse_str(_primera(fila, (cm.get("nombre"),) if cm.get("nombre") else _CLAVES_NOMBRE)),
            tipo_operacion=parse_str(_primera(fila, (cm.get("tipo_operacion"),) if cm.get("tipo_operacion") else _CLAVES_TIPO)),
            dia_pago=parse_int(_primera(fila, (cm.get("dia_pago"),) if cm.get("dia_pago") else _CLAVES_DIA_PAGO)),
            valor_cuota=parse_float(_primera(fila, (cm.get("valor_cuota"),) if cm.get("valor_cuota") else _CLAVES_CUOTA)),
            dias_mora=parse_int(_primera(fila, (cm.get("dias_mora"),) if cm.get("dias_mora") else _CLAVES_MORA)),
            fecha_concesion=parse_fecha_cadetacaco(_primera(fila, (cm.get("fecha_concesion"),) if cm.get("fecha_concesion") else _CLAVES_CONCESION)),
            fecha_corte=fecha_corte,
        ))

    log.info("%s → %d registros leídos", path.name, len(resultado))
    return resultado
