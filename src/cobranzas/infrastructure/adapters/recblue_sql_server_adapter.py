import logging
from typing import Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from cobranzas.domain.ports.recblue_port import RecbluePort

logger = logging.getLogger("cobranzas.recblue_sql")


def _normalizar_operacion(valor: object) -> str:
    """
    Normaliza número de operación para que coincida con los .lis, Recblue y BD local.

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


class RecblueSqlServerAdapter(RecbluePort):
    """
    Obtiene ID Crédito por número de operación desde Recblue SQL Server.

    Si falla Recblue, usa fallback local desde:

        BD_Cobranza.dbo.deuda
        BD_Cobranza.dbo.asesores_deuda

    Regla:
        - El proceso NO se detiene si falla Recblue.
        - Se notifica por correo.
        - Se usa el último id_credito_recblue guardado localmente.
    """

    def __init__(
        self,
        recblue_database_url: str,
        local_database_url: Optional[str] = None,
        settings: Optional[object] = None,
    ) -> None:
        self._recblue_database_url = recblue_database_url
        self._local_database_url = local_database_url
        self._settings = settings

        self._ultimos_errores: List[str] = []
        self._correo_fallo_enviado = False
        self._cache_mapa: Optional[Dict[str, str]] = None

        self._recblue_engine = create_engine(
            recblue_database_url,
            future=True,
            pool_pre_ping=True,
        )
        self._recblue_session_factory = sessionmaker(
            bind=self._recblue_engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )

        self._local_session_factory = None

        if local_database_url:
            self._local_engine = create_engine(
                local_database_url,
                future=True,
                pool_pre_ping=True,
            )
            self._local_session_factory = sessionmaker(
                bind=self._local_engine,
                autoflush=False,
                autocommit=False,
                future=True,
            )

    @property
    def errores_validacion(self) -> List[str]:
        return list(self._ultimos_errores)

    def id_credito_por_operacion(self) -> Dict[str, str]:
        """
        Devuelve:

            {
                numero_operacion: id_credito_recblue
            }

        Primero intenta Recblue.
        Si falla, usa BD local.
        """
        if self._cache_mapa is not None:
            return dict(self._cache_mapa)

        self._ultimos_errores = []

        try:
            mapa = self._leer_desde_recblue()

            self._cache_mapa = mapa

            logger.info(
                "Recblue SQL Server | CREDITOS activos cargados=%s",
                len(mapa),
            )

            return dict(mapa)

        except Exception as exc:
            mensaje = (
                "No se pudo consultar Recblue SQL Server. "
                "Se intentará usar fallback local desde BD_Cobranza."
            )

            logger.exception("%s | error=%s", mensaje, exc)

            self._ultimos_errores.append(f"{mensaje} Error: {exc}")

            self._notificar_fallo_recblue(exc)

            mapa_fallback = self._leer_desde_bd_local()

            self._cache_mapa = mapa_fallback

            logger.warning(
                "Recblue fallback local | operaciones cargadas desde BD_Cobranza=%s",
                len(mapa_fallback),
            )

            return dict(mapa_fallback)

    def _leer_desde_recblue(self) -> Dict[str, str]:
        sql = text(
            """
            SELECT
                numero_operacion,
                id_credito
            FROM CREDITOS
            WHERE estado_credito_cr = 'ACTIVO'
              AND numero_operacion IS NOT NULL
              AND id_credito IS NOT NULL
            """
        )

        with self._recblue_session_factory() as session:
            filas = session.execute(sql).mappings().all()

        mapa: Dict[str, str] = {}

        for fila in filas:
            numero_operacion = _normalizar_operacion(fila.get("numero_operacion"))
            id_credito = str(fila.get("id_credito") or "").strip()

            if not numero_operacion or not id_credito:
                continue

            if numero_operacion in mapa and mapa[numero_operacion] != id_credito:
                logger.warning(
                    "Recblue SQL duplicado | operacion=%s | anterior=%s | nuevo=%s",
                    numero_operacion,
                    mapa[numero_operacion],
                    id_credito,
                )

            mapa[numero_operacion] = id_credito

        return mapa

    def _leer_desde_bd_local(self) -> Dict[str, str]:
        """
        Fallback cuando Recblue no responde.

        Usa el último id_credito_recblue guardado localmente.
        """
        if self._local_session_factory is None:
            logger.warning(
                "Recblue fallback local omitido: no se configuró local_database_url"
            )
            return {}

        sql = text(
            """
            WITH ultimos AS (
                SELECT
                    RIGHT(
                        '0000000000' + LTRIM(RTRIM(CAST(d.numero_operacion AS VARCHAR(50)))),
                        10
                    ) AS numero_operacion,
                    LTRIM(RTRIM(CAST(ad.id_credito_recblue AS VARCHAR(100)))) AS id_credito_recblue,
                    ROW_NUMBER() OVER (
                        PARTITION BY RIGHT(
                            '0000000000' + LTRIM(RTRIM(CAST(d.numero_operacion AS VARCHAR(50)))),
                            10
                        )
                        ORDER BY
                            ad.fecha_modificacion DESC,
                            ad.fecha_asignacion DESC,
                            d.fecha_corte DESC,
                            ad.id_asesor_deuda DESC
                    ) AS rn
                FROM dbo.asesores_deuda ad
                INNER JOIN dbo.deuda d
                    ON d.id_deuda = ad.id_deuda
                WHERE d.numero_operacion IS NOT NULL
                  AND ad.id_credito_recblue IS NOT NULL
                  AND LTRIM(RTRIM(CAST(ad.id_credito_recblue AS VARCHAR(100)))) <> ''
            )
            SELECT
                numero_operacion,
                id_credito_recblue
            FROM ultimos
            WHERE rn = 1
            """
        )

        try:
            with self._local_session_factory() as session:
                filas = session.execute(sql).mappings().all()

            mapa: Dict[str, str] = {}

            for fila in filas:
                numero_operacion = _normalizar_operacion(fila.get("numero_operacion"))
                id_credito = str(fila.get("id_credito_recblue") or "").strip()

                if numero_operacion and id_credito:
                    mapa[numero_operacion] = id_credito

            return mapa

        except Exception as exc:
            logger.exception(
                "También falló el fallback local de Recblue desde BD_Cobranza | error=%s",
                exc,
            )
            self._ultimos_errores.append(
                f"También falló fallback local de Recblue desde BD_Cobranza: {exc}"
            )
            return {}

    def _notificar_fallo_recblue(self, exc: Exception) -> None:
        """
        Envía correo una sola vez por ejecución cuando Recblue falla.

        Si el correo falla, no se detiene el proceso.
        """
        if self._correo_fallo_enviado:
            return

        if self._settings is None:
            logger.warning(
                "No se envía correo por fallo Recblue: adapter sin settings"
            )
            return

        try:
            from cobranzas.jobs.notificar_error import notificar_error_pipeline

            fecha_corte = self._obtener_fecha_corte()

            notificar_error_pipeline(
                self._settings,
                origen="Recblue SQL Server - consulta CREDITOS",
                mensajes=[
                    "No se pudo consultar Recblue SQL Server.",
                    "El proceso continuará usando los id_credito_recblue almacenados en BD_Cobranza.",
                    "Fuente fallback: dbo.deuda + dbo.asesores_deuda.",
                    str(exc),
                ],
                fecha_corte=fecha_corte,
                exc=exc,
            )

            self._correo_fallo_enviado = True

            logger.info(
                "Correo enviado por fallo de Recblue SQL Server | fecha_corte=%s",
                fecha_corte,
            )

        except Exception as notify_exc:
            logger.exception(
                "No se pudo enviar correo por fallo de Recblue | "
                "error_original=%s | error_notificacion=%s",
                exc,
                notify_exc,
            )

    def _obtener_fecha_corte(self) -> str:
        fecha = getattr(self._settings, "fecha_corte", "")

        if not fecha:
            return ""

        try:
            if hasattr(fecha, "strftime"):
                return fecha.strftime("%m%d%Y")
            return str(fecha)
        except Exception:
            return str(fecha)

    def operaciones_por_id_credito(self, id_credito: str) -> List[Dict[str, str]]:
        id_buscado = str(id_credito or "").strip()

        if not id_buscado:
            return []

        mapa = self.id_credito_por_operacion()

        return [
            {
                "numero_operacion": numero_operacion,
                "id_credito_recblue": id_credito_recblue,
            }
            for numero_operacion, id_credito_recblue in mapa.items()
            if str(id_credito_recblue or "").strip().replace(".0", "")
            == id_buscado.replace(".0", "")
        ]

    def registro_por_operacion(self, numero_operacion: str) -> Optional[Dict[str, str]]:
        operacion = _normalizar_operacion(numero_operacion)

        if not operacion:
            return None

        mapa = self.id_credito_por_operacion()
        id_credito = mapa.get(operacion)

        if not id_credito:
            return None

        return {
            "id_credito_recblue": id_credito,
            "numero_operacion": operacion,
        }