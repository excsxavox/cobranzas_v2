"""Handler 5: Resuelve id_credito_rb desde credito_rb (BD compartida)."""

import logging

from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

from preventiva.application.chain.handler import PreventivaHandler
from preventiva.application.chain.preventiva_context import PreventivaContext

log = logging.getLogger("preventiva.chain.recblue")


class RecblueHandler(PreventivaHandler):
    """
    Lee credito_rb (tabla compartida con carteramora) para resolver
    numero_operacion → id_credito para el archivo Isabel.
    """

    def __init__(self, session_factory: sessionmaker, tabla: str = "credito_rb", **kwargs) -> None:
        super().__init__(**kwargs)
        self._sf = session_factory
        self._tabla = tabla

    def _procesar(self, ctx: PreventivaContext) -> PreventivaContext:
        operaciones = [r.operacion for r in ctx.seleccionados]
        if not operaciones:
            return ctx

        with self._sf() as session:
            filas = session.execute(
                text(
                    f"SELECT numero_operacion, id_credito "
                    f"FROM {self._tabla} "
                    f"WHERE numero_operacion IN :ops"
                ),
                {"ops": tuple(operaciones)},
            ).fetchall()

        ctx.id_creditos_rb = {fila[0]: fila[1] for fila in filas}

        for r in ctx.seleccionados:
            r.id_credito_rb = ctx.id_creditos_rb.get(r.operacion, "")

        resueltos = sum(1 for r in ctx.seleccionados if r.id_credito_rb)
        log.info(
            "Recblue: %d/%d IDs resueltos (tabla: %s)",
            resueltos, len(ctx.seleccionados), self._tabla,
        )
        return ctx
