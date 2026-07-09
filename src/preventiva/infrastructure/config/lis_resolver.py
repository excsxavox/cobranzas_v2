"""
Resolución de rutas de archivos .lis para preventiva-svc.

Reutiliza la convención y los patrones probados de carteramora:
  {base}/{año}/{MMDDYYYY}/cartera{MMDDYYYY}b/<archivo>.lis

Los patrones de nombre de archivo son PARAMETRIZABLES (HU líneas 142-144):
si COBIS cambia la nomenclatura o la extensión, se ajusta sin tocar código.
"""

from datetime import date
from pathlib import Path
from typing import List, Optional, Sequence

# Reutilización directa de carteramora ────────────────────────────────────────
from cobranzas.infrastructure.config.docsmora_resolver import (
    carpeta_lote_docsmora,
    PATRONES_CADETACACO,
    PATRONES_CADETACACO_LEGACY,
    PATRONES_CAMOROSICO,
)
from cobranzas.infrastructure.config.fecha_corte import fecha_corte_mmddyyyy
# ──────────────────────────────────────────────────────────────────────────────


def _candidatos(carpeta: Path, patron: str) -> List[Path]:
    """Archivos que cumplen el patrón, ignorando temporales de Office (~$)."""
    if not carpeta.is_dir():
        return []
    return [
        p for p in carpeta.glob(patron)
        if p.is_file() and not p.name.startswith("~$")
    ]


def _buscar(
    carpeta: Path,
    patrones: Sequence[str],
    fecha_mmddyyyy: str,
    patrones_legacy: Optional[Sequence[str]] = None,
) -> List[Path]:
    """
    Devuelve los archivos que cumplen alguno de los patrones, ordenados por
    fecha de modificación descendente (el más reciente primero). Igual criterio
    que carteramora: si hay varios, el primero es el vigente.
    """
    encontrados: List[Path] = []
    for plantilla in patrones:
        encontrados.extend(_candidatos(carpeta, plantilla.format(fecha=fecha_mmddyyyy)))

    if not encontrados and patrones_legacy:
        for plantilla in patrones_legacy:
            encontrados.extend(_candidatos(carpeta, plantilla.format(fecha=fecha_mmddyyyy)))

    # Dedupe y ordena por más reciente
    unicos = list({p.resolve(): p for p in encontrados}.values())
    unicos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return unicos


class LisResolver:
    """
    Resuelve rutas de CADETACACO y CAMOROSICO para una fecha dada.

    Patrones parametrizables: si se pasan `patrones_*` sobreescriben los de
    carteramora (usar `{fecha}` como marcador del MMDDYYYY).
    """

    def __init__(
        self,
        base_lis: Path,
        patrones_cadetacaco: Optional[Sequence[str]] = None,
        patrones_camorosico: Optional[Sequence[str]] = None,
    ) -> None:
        self._base = Path(base_lis)
        self._pat_cade = tuple(patrones_cadetacaco) if patrones_cadetacaco else PATRONES_CADETACACO
        self._pat_camo = tuple(patrones_camorosico) if patrones_camorosico else PATRONES_CAMOROSICO

    def _carpeta_lote(self, fecha: date) -> Path:
        return carpeta_lote_docsmora(self._base, fecha_corte_mmddyyyy(fecha))

    def cadetacaco(self, fecha: date) -> List[Path]:
        ftxt = fecha_corte_mmddyyyy(fecha)
        return _buscar(
            self._carpeta_lote(fecha),
            self._pat_cade,
            ftxt,
            patrones_legacy=PATRONES_CADETACACO_LEGACY,
        )

    def camorosico(self, fecha: date) -> List[Path]:
        ftxt = fecha_corte_mmddyyyy(fecha)
        return _buscar(self._carpeta_lote(fecha), self._pat_camo, ftxt)


class AhsaldiaResolver:
    """
    Resuelve el archivo AHSALDIA (servidor distinto, HU líneas 110-120).
    Estructura: {base}/{año}/<subcarpeta>/<ahsaldia...>.lis
    Patrón parametrizable con `{fecha}` opcional.
    """

    def __init__(
        self,
        base_ahsaldia: Path,
        patron: str = "ahsaldia*_of00255.lis",
    ) -> None:
        self._base = Path(base_ahsaldia)
        self._patron = patron

    def resolver(self, fecha: date) -> List[Path]:
        ftxt = fecha_corte_mmddyyyy(fecha)
        anio = str(fecha.year)
        patron_fmt = self._patron.format(fecha=ftxt) if "{fecha}" in self._patron else self._patron
        carpeta_anio = self._base / anio
        # Busca en el año vigente y subcarpetas (estructura diaria variable)
        base_busqueda = carpeta_anio if carpeta_anio.is_dir() else self._base
        return [
            p for p in base_busqueda.glob(f"**/{patron_fmt}")
            if p.is_file() and not p.name.startswith("~$")
        ]
