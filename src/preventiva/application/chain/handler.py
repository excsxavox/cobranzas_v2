"""Handler base para la cadena de responsabilidad de gestión preventiva."""

from abc import ABC, abstractmethod
from typing import Optional

from preventiva.application.chain.preventiva_context import PreventivaContext


class PreventivaHandler(ABC):

    def __init__(self, siguiente: Optional["PreventivaHandler"] = None) -> None:
        self._siguiente = siguiente

    def enlazar(self, siguiente: "PreventivaHandler") -> "PreventivaHandler":
        self._siguiente = siguiente
        return siguiente

    def manejar(self, ctx: PreventivaContext) -> PreventivaContext:
        if not ctx.ok:
            return ctx
        ctx = self._procesar(ctx)
        if self._siguiente is not None:
            return self._siguiente.manejar(ctx)
        return ctx

    @abstractmethod
    def _procesar(self, ctx: PreventivaContext) -> PreventivaContext:
        raise NotImplementedError
