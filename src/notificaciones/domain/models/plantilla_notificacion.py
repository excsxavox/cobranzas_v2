from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PlantillaNotificacion:
    id_proceso: str
    estado: str
    correo_para: str
    correo_copia: Optional[str]
    plantilla_correo: str
