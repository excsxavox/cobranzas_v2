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
        # Busca primero en la subcarpeta estructurada (producción)
        resultado = _buscar(
            self._carpeta_lote(fecha),
            self._pat_cade,
            ftxt,
            patrones_legacy=PATRONES_CADETACACO_LEGACY,
        )
        # Fallback: busca recursivamente en la raíz (pruebas locales)
        if not resultado:
            resultado = [
                p for patron in self._pat_cade
                for p in self._base.glob(f"**/{patron.format(fecha=ftxt)}")
                if p.is_file() and not p.name.startswith("~$")
            ]
        return resultado

    def camorosico(self, fecha: date) -> List[Path]:
        ftxt = fecha_corte_mmddyyyy(fecha)
        resultado = _buscar(self._carpeta_lote(fecha), self._pat_camo, ftxt)
        if not resultado:
            resultado = [
                p for patron in self._pat_camo
                for p in self._base.glob(f"**/{patron.format(fecha=ftxt)}")
                if p.is_file() and not p.name.startswith("~$")
            ]
        return resultado


class AhsaldiaResolver:
    """
    Resuelve el archivo AHSALDIA.
    Estructura: {base}/{YYYY}/{MMDDYYYY}/ahorros{MMDDYYYY}b/<ahsaldia>.lis
    Patrón parametrizable con `{fecha}` como marcador del MMDDYYYY.
    """

    def __init__(
        self,
        base_ahsaldia: Path,
        patron: str = "_{fecha}_*_of00255*",
    ) -> None:
        self._base = Path(base_ahsaldia)
        self._patron = patron

    def _carpeta_lote(self, fecha: date) -> Path:
        ftxt = fecha_corte_mmddyyyy(fecha)
        anio = ftxt[4:8]
        return self._base / anio / ftxt / f"ahorros{ftxt}b"

    def resolver(self, fecha: date) -> List[Path]:
        ftxt = fecha_corte_mmddyyyy(fecha)
        patron_fmt = self._patron.format(fecha=ftxt) if "{fecha}" in self._patron else self._patron

        # Busca primero en la subcarpeta estructurada (producción)
        carpeta = self._carpeta_lote(fecha)
        if carpeta.is_dir():
            resultado = [
                p for p in carpeta.glob(patron_fmt)
                if p.is_file() and not p.name.startswith("~$")
            ]
            if resultado:
                resultado.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                return resultado

        # Fallback: busca recursivamente desde la raíz (pruebas locales)
        return [
            p for p in self._base.glob(f"**/{patron_fmt}")
            if p.is_file() and not p.name.startswith("~$")
        ]
