"""
Genera el archivo PREVENTIVA_CORTE_DDMMAAAA.txt para Isabel.

Formato: pipe-separated (|)  →  telefono|nombre|id_credito_rb
(HU GRC-03, líneas 230-240)
"""

import logging
from datetime import date
from pathlib import Path
from typing import List

from preventiva.domain.models.registro_lis import RegistroSeleccion

log = logging.getLogger("preventiva.adapters.isabel")


def escribir_isabel(
    registros: List[RegistroSeleccion],
    directorio: Path,
    fecha: date,
    numero_gestion: int,
) -> Path:
    nombre = f"PREVENTIVA_CORTE_{fecha.strftime('%d%m%Y')}_G{numero_gestion}.txt"
    ruta = directorio / nombre
    ruta.parent.mkdir(parents=True, exist_ok=True)

    with ruta.open("w", encoding="utf-8") as f:
        for r in registros:
            telefono = (r.telefono or "").strip()
            nombre_socio = (r.nombre or "").strip()
            id_rb = (r.id_credito_rb or "").strip()
            f.write(f"{telefono}|{nombre_socio}|{id_rb}\n")

    log.info("Isabel: %s (%d registros)", ruta.name, len(registros))
    return ruta
