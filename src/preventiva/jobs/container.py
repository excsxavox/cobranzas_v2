"""
Composition root de preventiva-svc.
Ensambla todas las dependencias a partir de PreventivaSettings.
"""

from datetime import date
from pathlib import Path
from typing import Optional, Set

# Reutilización desde carteramora ─────────────────────────────────────────────
from cobranzas.infrastructure.persistence.repositories.feriados_calendario_repository import (
    SqlAlchemyFeriadosCalendarioRepository,
)
from cobranzas.infrastructure.persistence.session import get_session_factory
from cobranzas.infrastructure.adapters.smtp_correo_adapter import SmtpCorreoAdapter
# ─────────────────────────────────────────────────────────────────────────────

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
from preventiva.application.chain.preventiva_context import PreventivaContext


def _cargar_feriados(session_factory, clave: str) -> Set[date]:
    repo = SqlAlchemyFeriadosCalendarioRepository(session_factory, clave)
    return repo.fechas_vigentes()


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
    dias_retraso    = params_repo.obtener_int("dias_retraso_recurrente", cfg.prev_dias_retraso_recurrente)
    dias_antes      = params_repo.obtener_int("dias_antes_gestion", cfg.prev_dias_antes_gestion)
    # Días máximos a conservar en historial_mora_detalle (ventana deslizante)
    dias_retencion  = params_repo.obtener_int("dias_retencion_historial", 190)

    # Activación de cada tipo de filtro (parametrizable, default activo)
    c1_activo = params_repo.obtener_bool("filtro_mora_activo",        True)
    c2_activo = params_repo.obtener_bool("filtro_pago_tardio_activo", True)
    c3_activo = params_repo.obtener_bool("filtro_nuevo_activo",       True)
    c4_activo = params_repo.obtener_bool("filtro_alivio_activo",      True)
    excluir_saldo_total = params_repo.obtener_bool("excluir_cobertura_total", True)

    # Tipos de alivio desde dbo.catalogo (clave prev_alivio)
    tipos_alivio: Set[str] = set()
    try:
        from sqlalchemy import select, text
        with sf() as session:
            filas = session.execute(
                text("SELECT c.valor FROM dbo.catalogo c "
                     "JOIN dbo.claves k ON k.id_clave = c.id_clave "
                     "WHERE k.clave = 'prev_alivio' AND c.vigencia = 1")
            ).fetchall()
            tipos_alivio = {f[0].upper() for f in filas}
    except Exception:
        pass

    seleccion_svc   = SeleccionPreventivaService(
        umbral_mora_dias=umbral_mora,
        numero_meses=numero_meses,
        antiguedad_max_meses=antiguedad,
        dias_retraso_recurrente=dias_retraso,
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
    pat_ahsa = params_repo.obtener("AHSALDIA_LIS", "ahsaldia*_of00255.lis")

    lis_resolver = LisResolver(
        base_lis=Path(cfg.prev_origen_lis),
        patrones_cadetacaco=[pat_cade] if pat_cade else None,
        patrones_camorosico=[pat_camo] if pat_camo else None,
    )
    ahsaldia_resolver = AhsaldiaResolver(
        base_ahsaldia=Path(cfg.prev_origen_ahsaldia),
        patron=pat_ahsa or "ahsaldia*_of00255.lis",
    )

    # Cadena de responsabilidad (orden: 1→2→3→4→5→6→7)
    reporte   = ReporteHandler(reporte_repo=reporte_repo, directorio_salida=dir_salida)
    isabel    = IsabelHandler(directorio_salida=dir_salida)
    recblue   = RecblueHandler(session_factory=sf)
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
    )

    isabel.enlazar(reporte)
    recblue.enlazar(isabel)
    saldo.enlazar(recblue)
    seleccion.enlazar(saldo)
    historial.enlazar(seleccion)
    parse_lis.enlazar(historial)

    return parse_lis, historial_repo, calendario_svc, sf
