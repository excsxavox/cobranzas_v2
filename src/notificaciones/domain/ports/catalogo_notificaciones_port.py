from typing import Optional, Protocol

from notificaciones.domain.models.plantilla_notificacion import PlantillaNotificacion


class CatalogoNotificacionesPort(Protocol):
    def obtener(self, id_proceso: str, estado: str) -> Optional[PlantillaNotificacion]:
        ...
