import logging
import os
import re
from pathlib import Path
from typing import List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from cobranzas.domain.models.asesor_registro import AsesorRegistro
from cobranzas.domain.ports.asesor_excel_repository import AsesorExcelRepositoryPort

logger = logging.getLogger(__name__)

PREFIJO_CEDULA_ASESOR = "OF-"


def _texto(valor: object) -> str:
    if valor is None:
        return ""
    return str(valor).replace("\xa0", " ").strip()


def normalizar_cedula_asesor(valor: str) -> str:
    texto_valor = _texto(valor).upper()

    if not texto_valor:
        return ""

    if texto_valor.startswith(PREFIJO_CEDULA_ASESOR):
        return texto_valor

    solo_digitos = re.sub(r"\D", "", texto_valor)

    if solo_digitos and solo_digitos == re.sub(r"\D", "", texto_valor):
        return f"{PREFIJO_CEDULA_ASESOR}{solo_digitos.lstrip('0') or solo_digitos}"

    return f"{PREFIJO_CEDULA_ASESOR}{texto_valor}"


def _armar_nombre(nombres: str, apellidos: str, usuario: str) -> str:
    nombre_completo = f"{nombres} {apellidos}".strip()
    nombre_completo = re.sub(r"\s+", " ", nombre_completo)

    if nombre_completo:
        return nombre_completo.upper()

    return usuario.upper()


def _armar_telefono(
    telefono_1: str,
    telefono_2: str,
    extension: str,
) -> str:
    if telefono_1:
        return telefono_1

    if telefono_2:
        return telefono_2

    if extension:
        return extension

    return ""


class SqlServerAsesorReader(AsesorExcelRepositoryPort):
    """
    Lee asesores desde SQL Server.

    Reemplaza el consumo de:
        data/catalogo/asesores.xlsx

    Usa la conexión:
        RECBLUE_DATABASE_URL

    Si no existe, usa:
        DATABASE_URL

    Importante:
        Ya no usa columna ORDEN.
        El orden será el mismo orden en que SQL Server entrega los registros.
    """

    def __init__(self, database_url: Optional[str] = None) -> None:
        self._database_url = (
            database_url
            or os.getenv("RECBLUE_DATABASE_URL")
            or os.getenv("DATABASE_URL")
        )

    def leer_asesores(self, archivo_excel: Optional[Path] = None) -> List[AsesorRegistro]:
        """
        Se deja el parámetro archivo_excel para no romper el servicio actual,
        pero ya no se utiliza.
        """

        if not self._database_url:
            raise RuntimeError(
                "No está configurada la conexión para asesores. "
                "Defina RECBLUE_DATABASE_URL o DATABASE_URL en el .env."
            )

        query = text(
            """
            SELECT
                id_usuario,
                nombres_usr,
                apellidos_usr,
                usuario,
                ci_usr,
                estado_usr,
                nivel_usr,
                cobranzas_usr,
                telemercadeo_usr,
                actualizacion_usr,
                supervisor_usr,
                gerencia_usr,
                externo_usr,
                cedente,
                extension_usr,
                telefono_1_usr,
                telefono_2_usr,
                perfil_usuario,
                asignacion_usr,
                numasig_usr,
                observacion_usr,
                grupo_usr,
                agencia_usr,
                email_usr,
                codigo_app
            FROM BDDSICUIOCM01.dbo.USUARIOS
            WHERE perfil_usuario = 'NUBGESTOR'
              AND estado_usr = 'ACTIVO'
            """
        )

        registros: List[AsesorRegistro] = []

        try:
            engine = create_engine(self._database_url, pool_pre_ping=True)

            with engine.connect() as conn:
                result = conn.execute(query)

                for indice, row in enumerate(result, start=1):
                    usuario = _texto(row.usuario).upper()
                    nombres = _texto(row.nombres_usr)
                    apellidos = _texto(row.apellidos_usr)
                    ci_usr = _texto(row.ci_usr)
                    telefono_1 = _texto(row.telefono_1_usr)
                    telefono_2 = _texto(row.telefono_2_usr)
                    extension = _texto(row.extension_usr)
                    email = _texto(row.email_usr)
                    estado = _texto(row.estado_usr).upper()

                    if not usuario and not ci_usr:
                        logger.warning(
                            "Asesor omitido: usuario y ci_usr vacíos | fila=%s | id_usuario=%s",
                            indice,
                            _texto(row.id_usuario),
                        )
                        continue

                    cedula_base = ci_usr or usuario
                    cedula = normalizar_cedula_asesor(cedula_base)

                    nombre = _armar_nombre(nombres, apellidos, usuario)
                    telefono = _armar_telefono(telefono_1, telefono_2, extension)

                    registros.append(
                        AsesorRegistro(
                            cedula=cedula,
                            nombre=nombre,
                            numero_telefono=telefono,
                            email=email,
                            activo=(estado == "ACTIVO"),
                        )
                    )

            if not registros:
                raise ValueError(
                    "La consulta de asesores desde SQL Server no devolvió registros útiles."
                )

            logger.info(
                "Asesores leídos desde SQL Server | perfil=NUBGESTOR | activos=%s",
                len(registros),
            )

            return registros

        except SQLAlchemyError as e:
            logger.exception("Error consultando asesores desde SQL Server")
            raise RuntimeError(f"Error consultando asesores desde SQL Server: {e}") from e

        except Exception as e:
            logger.exception("Error inesperado consultando asesores desde SQL Server")
            raise RuntimeError(f"Error inesperado consultando asesores desde SQL Server: {e}") from e