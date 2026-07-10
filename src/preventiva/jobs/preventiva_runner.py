"""Ejecuta el pipeline de gestión preventiva para una fecha dada."""

import logging
from datetime import date, datetime
from typing import List, Optional, Set

from sqlalchemy import text

from preventiva.application.chain.preventiva_context import PreventivaContext
from preventiva.jobs.container import build_cadena
from preventiva.infrastructure.config.settings import PreventivaSettings

log = logging.getLogger("preventiva.runner")


def _generar_proceso_cod() -> str:
    return datetime.utcnow().strftime("%Y%m%d%H%M%S")


def _destinatarios_notificacion(session_factory, estado: str) -> List[str]:
    """Lee correos de dbo.notificaciones para el estado dado (HU líneas 147-149)."""
    try:
        with session_factory() as session:
            fila = session.execute(
                text(
                    "SELECT correo_para FROM notificaciones "
                    "WHERE id_proceso = 'general' AND estado = :estado AND activo = 1"
                ),
                {"estado": estado},
            ).fetchone()
        if fila and fila[0]:
            return [c.strip() for c in fila[0].split(";") if c.strip()]
    except Exception as exc:
        log.warning("No se pudieron leer destinatarios: %s", exc)
    return []


def _notificar(cfg: PreventivaSettings, session_factory, ctx: PreventivaContext) -> None:
    """Envía correo de resultado (OK/Error) reutilizando SmtpCorreoAdapter."""
    if not cfg.smtp_host:
        log.info("SMTP no configurado; se omite notificación.")
        return
    estado = "OK" if ctx.ok else "Error"
    destinatarios = _destinatarios_notificacion(session_factory, estado)
    if not destinatarios:
        return
    try:
        from cobranzas.infrastructure.adapters.smtp_correo_adapter import SmtpCorreoAdapter

        adapter = SmtpCorreoAdapter(
            host=cfg.smtp_host,
            port=cfg.smtp_port,
            usuario=cfg.smtp_user,
            password=cfg.smtp_password,
            remitente=cfg.smtp_from,
            usar_tls=cfg.smtp_use_tls,
        )
        if ctx.ok:
            asunto = f"[Gestión Preventiva] OK — {ctx.fecha_ejecucion:%d/%m/%Y} (gestión {ctx.numero_gestion})"
            cuerpo = (
                f"Proceso {ctx.proceso_cod} finalizado correctamente.\n"
                f"Seleccionados: {len(ctx.seleccionados)}\n"
                f"Archivo Isabel: {ctx.ruta_isabel}\n"
                f"Reporte: {ctx.ruta_reporte}"
            )
        else:
            asunto = f"[Gestión Preventiva] ERROR — {ctx.fecha_ejecucion:%d/%m/%Y}"
            cuerpo = (
                f"El proceso {ctx.proceso_cod} se detuvo con error.\n\n{ctx.mensaje_error}"
            )
        adapter.enviar(destinatarios, asunto, cuerpo)
        log.info("Notificación enviada a %d destinatario(s)", len(destinatarios))
    except Exception as exc:
        log.warning("Fallo al enviar notificación: %s", exc)


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
        ctx.mensaje_error = str(exc)
        historial_repo.cerrar(proceso_cod, estado="ERROR")

    # Notificación de resultado (HU líneas 139-149)
    _notificar(cfg, sf, ctx)

    return ctx
