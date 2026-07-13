"""Modelos de dominio para registros leídos de archivos .lis del core."""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class RegistroCadetacaco:
    """Fila del archivo CADETACACO (cartera vigente con detalle de cuota)."""

    operacion: str
    identificacion: str
    nombre: str
    tipo_operacion: str
    dia_pago: int
    valor_cuota: float
    dias_mora: int
    fecha_concesion: Optional[date]
    fecha_corte: Optional[date] = None


@dataclass(frozen=True)
class RegistroCamorosico:
    """Fila del archivo CAMOROSICO (detalle de mora histórica)."""

    operacion: str
    identificacion: str
    nombre: str
    dias_mora: int                  # DÍAS ATRASO del corte
    telefono: str = ""
    fecha_corte: Optional[date] = None
    fuente_archivo: str = ""


@dataclass(frozen=True)
class RegistroAhsaldia:
    """Fila del archivo AHSALDIA (saldo disponible en cuenta)."""

    identificacion: str
    saldo_disponible: float


@dataclass
class RegistroSeleccion:
    """Resultado de evaluación de criterios de selección para una operación."""

    operacion: str
    identificacion: str
    nombre: str
    telefono: str
    tipo_operacion: str
    dia_pago: int
    valor_cuota: float
    dias_mora_actual: int
    fecha_concesion: Optional[date]

    # Criterio 1: mora promedio > N días en últimos M meses
    promedio_meses: int = 0
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    criterio_mora: bool = False

    # Criterio 2: pago tardío recurrente
    criterio_pago_tardio: bool = False

    # Criterio 3: crédito nuevo ≤ M meses (incluye SIN validar mora)
    antiguedad_meses: int = 0
    criterio_nuevo: bool = False

    # Criterio 4: alivio financiero vigente (incluye SIN validar mora)
    criterio_alivio: bool = False

    # Decisión final (OR de los 4 criterios)
    aplica_gestion: bool = False

    # Validación de saldo (se completa en SaldoHandler)
    saldo_cuenta: float = 0.0
    valor_faltante: float = 0.0
    cobertura: str = "SIN_FONDOS"   # TOTAL / PARCIAL / SIN_FONDOS

    # Recblue (se resuelve en IsabelHandler)
    id_credito_rb: str = ""
