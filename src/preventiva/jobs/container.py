"""
Composition root de preventiva-svc.
Ensambla todas las dependencias a partir de PreventivaSettings.
"""

import logging
from pathlib import Path
from typing import Optional, Set

from cobranzas.infrastructure.persistence.session import get_session_factory

log = logging.getLogger("preventiva.container")

from preventiva.infrastructure.config.settings import PreventivaSettings
from preventiva.infrastructure.config.lis_resolver import AhsaldiaResolver, LisResolver
from preventiva.infrastructure.persistence.database import create_engine_preventiva, init_database
from preventiva.infrastructure.persistence.repositories.historial_proceso_repository import (
    HistorialProcesoRepository,
)
from preventiva.infrastructure.persistence.repositories.historial_mora_repository import (
    SqlAlchemyHistorialMoraRepository,
)
from preventiva.infrastructure.persistence.repositories.reporte_preventiva_repository import (
    SqlAlchemyReporteRepository,
)
from preventiva.infrastructure.persistence.repositories.parametros_repository import (
    SqlAlchemyParametrosRepository,
)
from preventiva.domain.services.seleccion_preventiva_service import SeleccionPreventivaService
from preventiva.domain.services.validar_saldo_service import ValidarSaldoService
from preventiva.domain.services.calendario_gestion_service import CalendarioGestionService

from preventiva.application.chain.parse_lis_handler import ParseLisHandler
from preventiva.application.chain.historial_mora_handler import HistorialMoraHandler
from preventiva.application.chain.seleccion_handler import SeleccionHandler
from preventiva.application.chain.saldo_handler import SaldoHandler
from preventiva.application.chain.recblue_handler import RecblueHandler
from preventiva.application.chain.isabel_handler import IsabelHandler
from preventiva.application.chain.reporte_handler import ReporteHandler
def build_cadena(settings: Optional[PreventivaSettings] = None):
    """Construye y retorna (cadena, historial_repo, calendario_svc, session_factory)."""
    cfg = settings or PreventivaSettings()

    engine = create_engine_preventiva(cfg.database_url, echo=cfg.db_echo)
    init_database(engine)
    sf = get_session_factory(engine)

    params_repo      = SqlAlchemyParametrosRepository(sf)
    historial_repo   = HistorialProcesoRepository(sf)
    mora_repo        = SqlAlchemyHistorialMoraRepository(sf)
    reporte_repo     = SqlAlchemyReporteRepository(sf)

    # Umbrales / días desde BD (o valores de settings como fallback)
    numero_meses    = params_repo.obtener_int("numero_meses",    cfg.prev_numero_meses)
    umbral_mora     = params_repo.obtener_int("promedio_gestion", cfg.prev_promedio_gestion)
    antiguedad      = params_repo.obtener_int("antiguedad",       cfg.prev_antiguedad)
    dias_retraso        = params_repo.obtener_int("dias_retraso_recurrente", cfg.prev_dias_retraso_recurrente)
    dias_antes          = params_repo.obtener_int("dias_antes_gestion", cfg.prev_dias_antes_gestion)
    # Días máximos a conservar en historial_mora_detalle (ventana deslizante)
    dias_retencion      = params_repo.obtener_int("dias_retencion_historial", 190)
    # C2: mínimo de meses con mora para ser considerado recurrente (HU líneas 63-66)
    meses_consistencia  = params_repo.obtener_int("meses_consistencia_c2", 5)

    # Activación de cada tipo de filtro (parametrizable, default activo)
    c1_activo = params_repo.obtener_bool("filtro_mora_activo",        True)
    c2_activo = params_repo.obtener_bool("filtro_pago_tardio_activo", True)
    c3_activo = params_repo.obtener_bool("filtro_nuevo_activo",       True)
    c4_activo = params_repo.obtener_bool("filtro_alivio_activo",      True)
    excluir_saldo_total = params_repo.obtener_bool("excluir_cobertura_total", True)

    # Tipos de alivio desde catalogo (clave prev_alivio)
    tipos_alivio: Set[str] = set()
    try:
        from sqlalchemy import text
        with sf() as session:
            filas = session.execute(
                text("SELECT c.valor FROM catalogo c "
                     "JOIN claves k ON k.id_clave = c.id_clave "
                     "WHERE k.clave = 'prev_alivio' AND c.vigencia = 1")
            ).fetchall()
            tipos_alivio = {f[0].upper() for f in filas}
    except Exception as exc:
        log.warning("No se pudieron leer tipos_alivio: %s", exc)

    seleccion_svc   = SeleccionPreventivaService(
        umbral_mora_dias=umbral_mora,
        antiguedad_max_meses=antiguedad,
        meses_consistencia=meses_consistencia,
        tipos_alivio=tipos_alivio,
        criterio_mora_activo=c1_activo,
        criterio_pago_tardio_activo=c2_activo,
        criterio_nuevo_activo=c3_activo,
        criterio_alivio_activo=c4_activo,
    )
    saldo_svc       = ValidarSaldoService(excluir_cobertura_total=excluir_saldo_total)
    calendario_svc  = CalendarioGestionService(dias_antes_gestion=dias_antes)

    dir_salida = Path(cfg.prev_directorio_resultados)

    # Patrones de archivo parametrizables (HU líneas 142-144). Si el parámetro
    # está vacío, LisResolver usa los patrones probados de carteramora.
    pat_cade = params_repo.obtener("CADETACACO_LIS", "")
    pat_camo = params_repo.obtener("CAMOROSICO_LIS", "")
    pat_ahsa = params_repo.obtener("AHSALDIA_LIS", "_{fecha}_*_of00255*")

    # Cabeceras de columnas parametrizables (HU líneas 167-168).
    # Si COBIS actualiza los nombres de columna, se ajusta en dbo.parametros
    # sin modificar código. Solo se sobrescriben las que estén definidas.
    _COL_KEYS = {
        "col_cade_operacion":      "operacion",
        "col_cade_identificacion": "identificacion",
        "col_cade_nombre":         "nombre",
        "col_cade_tipo_operacion": "tipo_operacion",
        "col_cade_dia_pago":       "dia_pago",
        "col_cade_valor_cuota":    "valor_cuota",
        "col_cade_dias_mora":      "dias_mora",
        "col_cade_fecha_concesion":"fecha_concesion",
    }
    col_map_cadetacaco = {
        campo: params_repo.obtener(param_key, "")
        for param_key, campo in _COL_KEYS.items()
        if params_repo.obtener(param_key, "")  # solo incluir si tiene valor
    }

    lis_resolver = LisResolver(
        base_lis=Path(cfg.directorio_docsmora),
        patrones_cadetacaco=[pat_cade] if pat_cade else None,
        patrones_camorosico=[pat_camo] if pat_camo else None,
    )
    ahsaldia_resolver = AhsaldiaResolver(
        base_ahsaldia=Path(cfg.prev_origen_ahsaldia),
        patron=pat_ahsa or "ahsaldia*_of00255.lis",
    )

    # Lee cortes activos para que ReporteHandler detecte el último del mes
    cortes_activos: Set[int] = set()
    try:
        from sqlalchemy import text
        with sf() as session:
            filas_c = session.execute(
                text("SELECT c.valor FROM catalogo c "
                     "JOIN claves k ON k.id_clave = c.id_clave "
                     "WHERE k.clave = 'prev_dias_corte' AND c.vigencia = 1")
            ).fetchall()
            for f in filas_c:
                for parte in str(f[0]).split(","):
                    if parte.strip().isdigit():
                        cortes_activos.add(int(parte.strip()))
    except Exception:
        pass

    # Cadena de responsabilidad (orden: 1→2→3→4→5→6→7)
    reporte   = ReporteHandler(
        reporte_repo=reporte_repo,
        directorio_salida=dir_salida,
        cortes_activos=cortes_activos,
    )
    isabel    = IsabelHandler(directorio_salida=dir_salida)
    recblue   = RecblueHandler(session_factory=sf, tabla=params_repo.obtener("recblue", "credito_rb"))
    saldo     = SaldoHandler(servicio=saldo_svc, resolver_ahsaldia=ahsaldia_resolver.resolver)
    seleccion = SeleccionHandler(servicio=seleccion_svc)
    historial = HistorialMoraHandler(
        historial_repo=mora_repo,
        numero_meses=numero_meses,
        dias_retencion=dias_retencion,
    )
    parse_lis = ParseLisHandler(
        resolver_cadetacaco=lis_resolver.cadetacaco,
        resolver_camorosico=lis_resolver.camorosico,
        col_map_cadetacaco=col_map_cadetacaco or None,
    )

    isabel.enlazar(reporte)
    recblue.enlazar(isabel)
    saldo.enlazar(recblue)
    seleccion.enlazar(saldo)
    historial.enlazar(seleccion)
    parse_lis.enlazar(historial)

    return parse_lis, historial_repo, calendario_svc, sf
