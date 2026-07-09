import logging
import re
from pathlib import Path
from typing import Dict, List

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from cobranzas.domain.models.asesor_registro import AsesorRegistro
from cobranzas.domain.ports.asesor_excel_repository import AsesorExcelRepositoryPort
from cobranzas.infrastructure.persistence.mappers.cobranza_credito_mapper import (
    PREFIJO_CEDULA_ASESOR,
)

logger = logging.getLogger("cobranzas.asesores.sql")


def normalizar_cedula_asesor(valor: object) -> str:
    """
    Mantiene la misma lógica del ExcelAsesorReader:
    - Si ya viene con prefijo, lo deja igual.
    - Si viene solo con números, agrega el prefijo usado por el sistema.
    """
    texto = str(valor or "").strip().upper()

    if not texto:
        return ""

    if texto.startswith(PREFIJO_CEDULA_ASESOR):
        return texto

    solo_digitos = re.sub(r"\D", "", texto)

    if solo_digitos and solo_digitos == re.sub(r"\D", "", texto):
        return f"{PREFIJO_CEDULA_ASESOR}{solo_digitos.lstrip('0') or solo_digitos}"

    return f"{PREFIJO_CEDULA_ASESOR}{texto}"


def _limpiar_texto(valor: object) -> str:
    return str(valor or "").replace("\xa0", " ").strip()


class SqlUsuariosAsesorReader(AsesorExcelRepositoryPort):
    """
    Reemplaza el Excel de asesores.

    Lee asesores desde SQL Server usando la misma conexión configurada para Recblue.

    Consulta:
        SELECT *
        FROM BDDSICUIOCM01.dbo.USUARIOS
        WHERE perfil_usuario = 'NUBGESTOR'
          AND estado_usr = 'ACTIVO'

    Importante:
        El campo AsesorRegistro.nombre se llena con USUARIOS.usuario.
        Esto se hace para que el archivo ASIGNACION_*.csv genere la columna
        USUARIO con el usuario del sistema, no con nombres_usr + apellidos_usr.
    """

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._engine = create_engine(
            database_url,
            future=True,
            pool_pre_ping=True,
        )
        self._session_factory = sessionmaker(
            bind=self._engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )

    def leer_asesores(self, archivo_excel: Path) -> List[AsesorRegistro]:
        """
        El parámetro archivo_excel se conserva solo para respetar el puerto actual.
        Ya no se usa ningún archivo Excel.
        """

        sql = text(
            """
            SELECT
                id_usuario,
                nombres_usr,
                apellidos_usr,
                usuario,
                ci_usr,
                estado_usr,
                perfil_usuario,
                telefono_1_usr,
                telefono_2_usr,
                email_usr
            FROM BDDSICUIOCM01.dbo.USUARIOS
            WHERE perfil_usuario = 'NUBGESTOR'
              AND estado_usr = 'ACTIVO'
            ORDER BY usuario
            """
        )

        with self._session_factory() as session:
            filas = session.execute(sql).mappings().all()

        registros: List[AsesorRegistro] = []
        cedulas_vistas: Dict[str, str] = {}

        for fila in filas:
            usuario = _limpiar_texto(fila.get("usuario"))
            cedula = normalizar_cedula_asesor(fila.get("ci_usr"))

            telefono = (
                _limpiar_texto(fila.get("telefono_1_usr"))
                or _limpiar_texto(fila.get("telefono_2_usr"))
            )

            email = _limpiar_texto(fila.get("email_usr"))

            if not cedula and not usuario:
                continue

            if not cedula:
                raise ValueError(
                    f"Usuario {usuario}: falta ci_usr para sincronizar asesor"
                )

            if not usuario:
                raise ValueError(
                    f"Asesor con cédula {cedula}: falta columna usuario"
                )

            if cedula in cedulas_vistas:
                logger.warning(
                    "Asesor SQL duplicado por cédula | cedula=%s | usuario_anterior=%s | usuario_actual=%s",
                    cedula,
                    cedulas_vistas[cedula],
                    usuario,
                )
                continue

            cedulas_vistas[cedula] = usuario

            registros.append(
                AsesorRegistro(
                    cedula=cedula,
                    nombre=usuario,
                    numero_telefono=telefono,
                    email=email,
                    activo=True,
                )
            )

        if not registros:
            raise ValueError(
                "No se encontraron asesores activos en "
                "BDDSICUIOCM01.dbo.USUARIOS con perfil_usuario='NUBGESTOR' "
                "y estado_usr='ACTIVO'"
            )

        logger.info(
            "Asesores SQL cargados | tabla=BDDSICUIOCM01.dbo.USUARIOS | total=%s | campo_usuario=usuario",
            len(registros),
        )

        return registros