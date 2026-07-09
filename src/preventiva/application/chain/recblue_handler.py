"""Handler 5: Resuelve id_credito_rb desde dbo.credito_rb (BD compartida)."""

import logging
from typing import List

from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

from preventiva.application.chain.handler import PreventivaHandler
from preventiva.application.chain.preventiva_context import PreventivaContext

log = logging.getLogger("preventiva.chain.recblue")


class RecblueHandler(PreventivaHandler):
    """
    Lee dbo.credito_rb (tabla compartida con carteramora) para resolver
    numero_operacion → id_credito para el archivo Isabel.
    """

    def __init__(self, session_factory: sessionmaker, **kwargs) -> None:
        super().__init__(**kwargs)
        self._sf = session_factory

    def _procesar(self, ctx: PreventivaContext) -> PreventivaContext:
        operaciones = [r.operacion for r in ctx.seleccionados]
        if not operaciones:
            return ctx

        placeholders = ",".join(f"'{op}'" for op in operaciones)
        sql = text(
            f"SELECT numero_operacion, id_credito FROM dbo.credito_rb "
            f"WHERE numero_operacion IN ({placeholders})"
        )
        with self._sf() as session:
            filas = session.execute(sql).fetchall()

        ctx.id_creditos_rb = {fila[0]: fila[1] for fila in filas}

        for r in ctx.seleccionados:
            r.id_credito_rb = ctx.id_creditos_rb.get(r.operacion, "")

        resueltos = sum(1 for r in ctx.seleccionados if r.id_credito_rb)
        log.info("Recblue: %d/%d IDs resueltos", resueltos, len(ctx.seleccionados))
        return ctx
