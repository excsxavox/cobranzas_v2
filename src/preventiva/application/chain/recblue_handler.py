"""Handler 5: Resuelve id_credito_rb desde credito_rb (BD compartida)."""

import logging
from typing import List

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from preventiva.application.chain.handler import PreventivaHandler
from preventiva.application.chain.preventiva_context import PreventivaContext

log = logging.getLogger("preventiva.chain.recblue")

_CHUNK = 900


class RecblueHandler(PreventivaHandler):
    """
    Lee credito_rb (tabla compartida con carteramora) para resolver
    numero_operacion → id_credito para el archivo Isabel.
    Usa la tabla sin prefijo de esquema para compatibilidad SQLite/SQL Server.
    """

    def __init__(self, session_factory: sessionmaker, tabla: str = "credito_rb", **kwargs) -> None:
        super().__init__(**kwargs)
        self._sf = session_factory
        self._tabla = tabla  # configurable desde dbo.parametros (clave "recblue")

    def _procesar(self, ctx: PreventivaContext) -> PreventivaContext:
        operaciones = [r.operacion for r in ctx.seleccionados]
        if not operaciones:
            return ctx

        id_creditos: dict = {}

        with self._sf() as session:
            for i in range(0, len(operaciones), _CHUNK):
                chunk = operaciones[i: i + _CHUNK]
                placeholders = ",".join(f"'{op}'" for op in chunk)
                sql = text(
                    f"SELECT numero_operacion, id_credito FROM {self._tabla} "
                    f"WHERE numero_operacion IN ({placeholders})"
                )
                filas = session.execute(sql).fetchall()
                for fila in filas:
                    id_creditos[fila[0]] = fila[1]

        ctx.id_creditos_rb = id_creditos

        for r in ctx.seleccionados:
            r.id_credito_rb = ctx.id_creditos_rb.get(r.operacion, "")

        resueltos = sum(1 for r in ctx.seleccionados if r.id_credito_rb)
        log.info("Recblue: %d/%d IDs resueltos (tabla: %s)", resueltos, len(ctx.seleccionados), self._tabla)
        return ctx
