from typing import Mapping, Optional


def render(plantilla: str, variables: Optional[Mapping[str, str]] = None) -> str:
    """Reemplaza {clave} en la plantilla con los valores provistos."""
    cuerpo = plantilla or ""
    for clave, valor in (variables or {}).items():
        cuerpo = cuerpo.replace("{" + clave + "}", str(valor))
    return cuerpo


def parse_emails(raw: Optional[str]) -> list[str]:
    """Parsea correos separados por punto y coma."""
    if not raw:
        return []
    return [correo.strip() for correo in raw.split(";") if correo.strip()]
