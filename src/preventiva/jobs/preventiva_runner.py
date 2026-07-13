"""Ejecuta el pipeline de gestión preventiva para una fecha dada."""

import logging
from datetime import date, datetime
from typing import List, Optional, Set

from preventiva.application.chain.preventiva_context import PreventivaContext
from preventiva.jobs.container import build_cadena
from preventiva.infrastructure.config.settings import PreventivaSettings

log = logging.getLogger("preventiva.runner")

_ASUNTO_PREFIX = "[BOT COBRANZA PREVENTIVA]"


def _generar_proceso_cod() -> str:
    return datetime.utcnow().strftime("%Y%m%d%H%M%S")


def _adjuntos_resultado(ctx: PreventivaContext) -> List[str]:
    adjuntos: List[str] = []
    if ctx.ruta_isabel:
        adjuntos.append(str(ctx.ruta_isabel))
    if ctx.numero_gestion == 3 and ctx.ruta_reporte:
        adjuntos.append(str(ctx.ruta_reporte))
    return adjuntos


def _notificar(ctx: PreventivaContext) -> None:
    """Envía correo de resultado vía API compartida de notificaciones."""
    from notificaciones import build_notificaciones_api_client

    client = build_notificaciones_api_client()
    fecha_str = ctx.fecha_ejecucion.strftime("%d/%m/%Y")

    if ctx.ok:
        resultado = client.enviar(
            id_proceso="proceso_completo",
            estado="OK",
            asunto=f"{_ASUNTO_PREFIX} Proceso {fecha_str} finalizado OK",
            variables={
                "fecha": fecha_str,
                "numero_gestion": str(ctx.numero_gestion),
                "proceso_cod": ctx.proceso_cod,
            },
            adjuntos=_adjuntos_resultado(ctx),
        )
    else:
        paso = ctx.paso_fallido or "pipeline_preventiva"
        resultado = client.notificar_error(
            id_proceso=paso if paso != "pipeline_preventiva" else "general",
            paso=paso,
            causa=ctx.mensaje_error or "Error desconocido en pipeline preventiva",
            proceso_cod=ctx.proceso_cod,
            asunto_prefix=_ASUNTO_PREFIX,
        )

    if resultado.enviado:
        log.info(
            "Notificación enviada a %d destinatario(s)",
            len(resultado.destinatarios),
        )
    elif resultado.omitido_motivo:
        log.warning("Notificación omitida: %s", resultado.omitido_motivo)
    else:
        for error in resultado.errores:
            log.warning("Fallo al enviar notificación: %s", error)


def ejecutar_preventiva(
    fecha_ejecucion: Optional[date] = None,
    dia_corte: Optional[int] = None,
    modo: str = "corte",
    settings: Optional[PreventivaSettings] = None,
) -> PreventivaContext:
    """
    Punto de entrada principal del pipeline.
    - fecha_ejecucion: fecha del proceso (por defecto hoy)
    - dia_corte: día de corte que disparó la ejecución (ej. 15)
    - modo: 'corte' | 'diario' | 'manual'
    """
    cfg = settings or PreventivaSettings()
    hoy = fecha_ejecucion or date.today()
    proceso_cod = _generar_proceso_cod()

    cadena, historial_repo, calendario_svc, sf = build_cadena(cfg)

    # Resolver número de gestión y dia_corte
    feriados: Set[date] = set()
    try:
        from cobranzas.infrastructure.persistence.repositories.feriados_calendario_repository import (
            SqlAlchemyFeriadosCalendarioRepository,
        )
        repo_f = SqlAlchemyFeriadosCalendarioRepository(sf, cfg.clave_feriados)
        feriados = repo_f.fechas_vigentes()
    except Exception as e:
        log.warning("No se pudieron cargar feriados: %s", e)

    if dia_corte is None:
        dia_corte = hoy.day

    numero_gestion = 1
    try:
        numero_gestion = calendario_svc.numero_gestion_para(
            hoy, hoy.year, hoy.month, dia_corte, feriados
        )
    except ValueError as e:
        log.warning("numero_gestion no determinado (%s) → se asume 1", e)

    log.info(
        "Iniciando proceso cod=%s  fecha=%s  corte=%s  gestión=%s  modo=%s",
        proceso_cod, hoy, dia_corte, numero_gestion, modo,
    )

    historial_repo.crear(proceso_cod, dia_corte=dia_corte, numero_gestion=numero_gestion, modo=modo)

    ctx = PreventivaContext(
        proceso_cod=proceso_cod,
        fecha_ejecucion=hoy,
        dia_corte=dia_corte,
        numero_gestion=numero_gestion,
        modo=modo,
        feriados=feriados,
    )

    try:
        ctx = cadena.manejar(ctx)
        historial_repo.cerrar(proceso_cod, estado="OK" if ctx.ok else "ERROR")
        historial_repo.log(
            proceso_cod,
            proceso_ejecutado="pipeline_preventiva",
            estado="OK" if ctx.ok else "ERROR",
            descripcion=ctx.mensaje_error or None,
            total=len(ctx.seleccionados),
        )
    except Exception as exc:
        log.exception("Error en pipeline preventiva: %s", exc)
        ctx.ok = False
        ctx.paso_fallido = ctx.paso_fallido or "pipeline_preventiva"
        ctx.mensaje_error = str(exc)
        historial_repo.cerrar(proceso_cod, estado="ERROR")

    # Notificación de resultado (HU líneas 139-149)
    _notificar(ctx)

    return ctx
