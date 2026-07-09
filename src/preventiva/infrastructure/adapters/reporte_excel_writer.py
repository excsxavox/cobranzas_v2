"""
Genera el reporte REPORTE_PREVENTIVA_DDMMAAAA.xlsx.

Columnas según HU GRC-03 líneas 289-308:
  Fecha proceso | Nombre | Cédula | Numero Operación | Dias mora |
  Día pago | Teléfono Celular | Saldo pendiente | Saldo en cuenta | Gestión N°
"""

import logging
from datetime import date
from pathlib import Path
from typing import List

import openpyxl
from openpyxl.styles import Font, PatternFill

from preventiva.domain.models.registro_lis import RegistroSeleccion

log = logging.getLogger("preventiva.adapters.reporte_excel")

CABECERAS = [
    "Fecha Proceso", "Nombre", "Cédula", "Numero Operación",
    "Días Mora", "Día Pago", "Teléfono Celular",
    "Saldo Pendiente Cuota", "Saldo en Cuenta", "Cobertura", "Gestión N°",
]

_HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
_HEADER_FONT = Font(color="FFFFFF", bold=True)


def escribir_reporte(
    registros: List[RegistroSeleccion],
    directorio: Path,
    fecha: date,
    numero_gestion: int,
) -> Path:
    nombre = f"REPORTE_PREVENTIVA_{fecha.strftime('%d%m%Y')}_G{numero_gestion}.xlsx"
    ruta = directorio / nombre
    ruta.parent.mkdir(parents=True, exist_ok=True)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Gestión {numero_gestion}"

    for col, cab in enumerate(CABECERAS, 1):
        cell = ws.cell(row=1, column=col, value=cab)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT

    for fila, r in enumerate(registros, 2):
        ws.cell(row=fila, column=1,  value=fecha.strftime("%d/%m/%Y"))
        ws.cell(row=fila, column=2,  value=r.nombre)
        ws.cell(row=fila, column=3,  value=r.identificacion)
        ws.cell(row=fila, column=4,  value=r.operacion)
        ws.cell(row=fila, column=5,  value=r.dias_mora_actual)
        ws.cell(row=fila, column=6,  value=r.dia_pago)
        ws.cell(row=fila, column=7,  value=r.telefono)
        ws.cell(row=fila, column=8,  value=r.valor_faltante)
        ws.cell(row=fila, column=9,  value=r.saldo_cuenta)
        ws.cell(row=fila, column=10, value=r.cobertura)
        ws.cell(row=fila, column=11, value=numero_gestion)

    wb.save(ruta)
    log.info("Reporte Excel: %s (%d filas)", ruta.name, len(registros))
    return ruta
