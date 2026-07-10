from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class MensajeCorreo:
    asunto: str
    cuerpo: str
    para: Sequence[str]
    cc: Sequence[str] = ()
    adjuntos: Sequence[Path] = ()
