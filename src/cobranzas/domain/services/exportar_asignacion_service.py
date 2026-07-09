import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional

from cobranzas.domain.models.asignacion_credito import AsignacionCredito

logger = logging.getLogger("cobranzas.asignacion.export")

COLUMNAS_CSV = ("ID_CREDITO", "USUARIO")


def _csv_tiene_filas_datos(ruta: Path) -> bool:
    if not ruta.is_file():
        return False

    with ruta.open(encoding="utf-8-sig", newline="") as fh:
        return any(True for _ in csv.DictReader(fh))


def _normalizar_operacion(valor: object) -> str:
    """
    Normaliza número de operación para cruce contra Recblue SQL/Excel.

    Ejemplos:
    - 18645311    -> 0018645311
    - 18645311.0  -> 0018645311
    - 0018645311  -> 0018645311
    """
    texto = str(valor or "").strip()

    if texto.endswith(".0"):
        texto = texto[:-2]

    texto = "".join(ch for ch in texto if ch.isdigit())

    if texto:
        texto = texto.zfill(10)

    return texto


class ExportarAsignacionService:
    def exportar_csv(
        self,
        ruta: Path,
        asignaciones: List[AsignacionCredito],
        ids_recblue_por_operacion: Optional[Dict[str, str]] = None,
        solo_nuevas: bool = True,
    ) -> None:
        """
        Genera ASIGNACION.csv con columnas:

        ID_CREDITO,USUARIO

        Regla importante:
        - Las filas salen SOLO desde la lista `asignaciones`.
        - Recblue SQL/Excel solo se usa para completar el ID_CREDITO.
        - Nunca se debe recorrer todo `ids_recblue_por_operacion`, porque puede
          traer miles de créditos activos y generar registros extra.

        Por defecto solo exporta asignaciones nuevas del día:
        - reasignado=True

        Si no hay filas nuevas y ya existe un CSV con datos, no se sobrescribe.
        """

        mapa_recblue = {
            _normalizar_operacion(numero): str(id_credito or "").strip()
            for numero, id_credito in (ids_recblue_por_operacion or {}).items()
            if _normalizar_operacion(numero) and str(id_credito or "").strip()
        }

        filas_export: List[Dict[str, str]] = []
        operaciones_exportadas = set()

        omitidas_sin_recblue = 0
        conservadas_bd = 0
        duplicadas = 0

        for fila in asignaciones:
            numero_operacion = _normalizar_operacion(fila.numero_operacion)

            if not numero_operacion:
                omitidas_sin_recblue += 1
                continue

            if solo_nuevas and not fila.reasignado:
                conservadas_bd += 1
                continue

            if numero_operacion in operaciones_exportadas:
                duplicadas += 1
                continue

            id_credito = (
                mapa_recblue.get(numero_operacion)
                or str(fila.id_credito_recblue or "").strip()
            )

            if not id_credito:
                omitidas_sin_recblue += 1
                continue

            usuario = str(fila.nombre_asesor or fila.codigo_asesor or "").strip()

            filas_export.append(
                {
                    "ID_CREDITO": id_credito,
                    "USUARIO": usuario,
                }
            )
            operaciones_exportadas.add(numero_operacion)

        if not filas_export:
            if _csv_tiene_filas_datos(ruta):
                logger.info(
                    "ASIGNACION.csv sin cambios: %s "
                    "(0 nuevas; se conserva el archivo existente)",
                    ruta,
                )
                return

            logger.info(
                "ASIGNACION.csv omitido: %s "
                "(0 filas exportables; sin archivo previo)",
                ruta,
            )
            return

        ruta.parent.mkdir(parents=True, exist_ok=True)

        with ruta.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNAS_CSV)
            writer.writeheader()
            writer.writerows(filas_export)

        if omitidas_sin_recblue:
            logger.warning(
                "ASIGNACION.csv: %s filas omitidas sin ID_CREDITO Recblue",
                omitidas_sin_recblue,
            )

        if duplicadas:
            logger.warning(
                "ASIGNACION.csv: %s operaciones duplicadas omitidas",
                duplicadas,
            )

        logger.info(
            "ASIGNACION.csv generado: %s | exportadas=%s | conservadas_bd=%s | "
            "sin_recblue=%s | duplicadas=%s | asignaciones_recibidas=%s | mapa_recblue=%s",
            ruta,
            len(filas_export),
            conservadas_bd,
            omitidas_sin_recblue,
            duplicadas,
            len(asignaciones),
            len(mapa_recblue),
        )