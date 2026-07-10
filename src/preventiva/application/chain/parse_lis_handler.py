"""
Handler 1: Lee y valida los archivos CADETACACO y CAMOROSICO del día.

Responsabilidades:
  1. Resolver rutas de los archivos .lis del día.
  2. Verificar existencia — si falta alguno, detener el proceso (HU líneas 139-140).
  3. Leer y parsear los archivos (formato TSV con cabeceras parametrizables).
  4. Validar integridad básica (HU línea 153):
       - El archivo CADETACACO no puede estar vacío.
       - Las columnas mínimas requeridas deben existir (si no, el reader devuelve 0 filas).
"""

import logging
from datetime import date
from pathlib import Path
from typing import Callable, Dict, List, Optional

from preventiva.application.chain.handler import PreventivaHandler
from preventiva.application.chain.preventiva_context import PreventivaContext
from preventiva.infrastructure.adapters.lis_cadetacaco_reader import leer_cadetacaco
from preventiva.infrastructure.adapters.lis_camorosico_reader import leer_camorosico

log = logging.getLogger("preventiva.chain.parse_lis")

# Columnas mínimas que deben estar presentes para considerar el archivo íntegro
_COLUMNAS_MINIMAS_CADE = {"operacion", "dias_mora", "dia_pago", "tipo_operacion", "valor_cuota"}


class ParseLisHandler(PreventivaHandler):
    """
    Lee los archivos .lis del día y valida su integridad antes del procesamiento.

    - CADETACACO: cartera vigente (criterios de selección y cuota).
    - CAMOROSICO: mora del día (para historial 6 meses).

    Parámetros:
        col_map_cadetacaco — sobreescribe nombres de columna del CADETACACO
                             (HU líneas 167-168; se carga desde dbo.parametros).
    """

    def __init__(
        self,
        resolver_cadetacaco: Callable[[date], List[Path]],
        resolver_camorosico: Callable[[date], List[Path]],
        col_map_cadetacaco: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._resolver_cade = resolver_cadetacaco
        self._resolver_camo = resolver_camorosico
        self._col_map = col_map_cadetacaco or {}

    def _procesar(self, ctx: PreventivaContext) -> PreventivaContext:
        rutas_cade = self._resolver_cade(ctx.fecha_ejecucion)
        rutas_camo = self._resolver_camo(ctx.fecha_ejecucion)

        # ── 1. Verificar existencia de archivos (HU líneas 139-140) ─────────
        faltantes = []
        if not rutas_cade:
            faltantes.append("CADETACACO")
        if not rutas_camo:
            faltantes.append("CAMOROSICO")
        if faltantes:
            ctx.ok = False
            ctx.paso_fallido = "parse_lis"
            ctx.mensaje_error = (
                "No se encontraron los archivos requeridos: "
                + ", ".join(faltantes)
                + f" para la fecha {ctx.fecha_ejecucion:%d/%m/%Y}. "
                "Regularice los archivos y ejecute el bot manualmente."
            )
            log.error(ctx.mensaje_error)
            return ctx

        # ── 2. Parsear archivos (cabeceras parametrizables vía col_map) ──────
        for path in rutas_cade:
            ctx.registros_cadetacaco.extend(
                leer_cadetacaco(
                    path,
                    fecha_corte=ctx.fecha_ejecucion,
                    col_map=self._col_map if self._col_map else None,
                )
            )

        for path in rutas_camo:
            ctx.registros_camorosico.extend(
                leer_camorosico(path, fecha_corte=ctx.fecha_ejecucion)
            )

        # ── 3. Validación de integridad (HU línea 153) ───────────────────────
        # Si CADETACACO tiene 0 registros con archivos presentes, significa que
        # las columnas no coinciden con las cabeceras configuradas.
        if len(ctx.registros_cadetacaco) == 0:
            ctx.ok = False
            ctx.paso_fallido = "parse_lis"
            ctx.mensaje_error = (
                f"CADETACACO ({rutas_cade[0].name}) no contiene registros válidos. "
                "Verifique que las cabeceras del archivo coincidan con las columnas "
                "configuradas en dbo.parametros (col_cade_*)."
            )
            log.error(ctx.mensaje_error)
            return ctx

        log.info(
            "ParseLis OK: cadetacaco=%d  camorosico=%d  [col_map=%s]",
            len(ctx.registros_cadetacaco),
            len(ctx.registros_camorosico),
            "personalizado" if self._col_map else "default",
        )
        return ctx
