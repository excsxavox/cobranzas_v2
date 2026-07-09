"""Schemas Pydantic para la API REST de gestión preventiva."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class EjecutarPreventivaRequest(BaseModel):
    fecha: Optional[str] = Field(None, description="DDMMAAAA; vacío = hoy")
    corte: Optional[int] = Field(None, description="Día de corte (ej. 15)")
    modo:  str           = Field("manual", description="corte | diario | manual")


class EjecutarPreventivaResponse(BaseModel):
    proceso_cod:      str
    estado:           str
    seleccionados:    int
    archivo_isabel:   Optional[str]
    archivo_reporte:  Optional[str]
    mensaje_error:    Optional[str]


# ── Historial de ejecuciones ──────────────────────────────────────────────────

class HistorialProcesoResponse(BaseModel):
    proceso_cod:    str
    fecha_inicio:   datetime
    fecha_fin:      Optional[datetime]
    estado:         str
    numero_gestion: Optional[int]
    dia_corte:      Optional[int]
    modo:           str


class PasoEjecucionResponse(BaseModel):
    id:              int
    paso_ejecucion:  str
    estado:          str
    descripcion:     Optional[str]
    total_registros: Optional[int]
    fecha_registro:  datetime


class LogCpResponse(BaseModel):
    id:                int
    proceso_ejecutado: str
    estado:            str
    descripcion:       Optional[str]
    total_registros:   Optional[int]
    tiempo_total:      Optional[str]
    fecha_hora:        datetime


# ── Reporte de gestiones ──────────────────────────────────────────────────────

class ReporteGestionResponse(BaseModel):
    numero_operacion: Optional[str]
    nombre:           Optional[str]
    cedula:           Optional[str]
    telefono:         Optional[str]
    dia_pago:         Optional[int]
    dias_mora:        Optional[int]
    saldo_cuenta:     Optional[float]
    saldo_pendiente:  Optional[float]
    numero_gestion:   int
    dia_corte:        Optional[int]
    fecha_proceso:    str


# ── Días de corte ─────────────────────────────────────────────────────────────

class DiaCorteResponse(BaseModel):
    valor:    str
    vigencia: bool


# ── Parámetros ────────────────────────────────────────────────────────────────

class ParametroResponse(BaseModel):
    nombre:      str
    valor:       Optional[str]
    descripcion: Optional[str]
    activo:      bool


class ParametroUpdateRequest(BaseModel):
    valor: str
