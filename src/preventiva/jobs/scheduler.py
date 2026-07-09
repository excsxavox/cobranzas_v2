"""
Scheduler de Gestión Preventiva.

Corre el pipeline una vez al día en el horario configurado en .env:
  PREV_SCHEDULER_HORA    — hora de disparo (0-23),  defecto 6
  PREV_SCHEDULER_MINUTO  — minuto de disparo (0-59), defecto 30
  PREV_SCHEDULER_TZ      — zona horaria (p.ej. America/Guayaquil)
  PREV_SCHEDULER_DIAS    — días de la semana (p.ej. mon,tue,wed,thu,fri)

El scheduler detecta si hoy hay un día de corte activo y ejecuta el pipeline
solo para ese corte (modo 'corte'). Si no hay corte activo, omite la ejecución
salvo que PREV_EJECUCION_CORTE=false, en cuyo caso corre en modo 'diario'.
"""

import logging
import signal
import sys
from datetime import date
from typing import Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from preventiva.infrastructure.config.settings import PreventivaSettings

log = logging.getLogger("preventiva.scheduler")


def _resolver_dia_corte(cfg: PreventivaSettings, hoy: date) -> Optional[int]:
    """
    Consulta dbo.catalogo (clave prev_dias_corte) para ver si HOY es un día
    en que debe ejecutarse el proceso de corte.

    Retorna el dia_corte si aplica, o None si no hay corte para hoy.
    """
    if not cfg.prev_ejecucion_corte:
        return hoy.day   # modo diario: siempre ejecuta

    try:
        from cobranzas.infrastructure.persistence.session import get_session_factory
        from preventiva.infrastructure.persistence.database import create_engine_preventiva
        from sqlalchemy import text

        engine = create_engine_preventiva(cfg.database_url, echo=False)
        sf = get_session_factory(engine)
        with sf() as session:
            # dias_corte guardados como "5,10,15,20,25,30" o filas individuales
            filas = session.execute(
                text(
                    "SELECT c.valor FROM dbo.catalogo c "
                    "JOIN dbo.claves k ON k.id_clave = c.id_clave "
                    "WHERE k.clave = 'prev_dias_corte' AND c.vigencia = 1"
                )
            ).fetchall()

        dias_corte = set()
        for fila in filas:
            for parte in str(fila[0]).split(","):
                parte = parte.strip()
                if parte.isdigit():
                    dias_corte.add(int(parte))

        if hoy.day in dias_corte:
            return hoy.day

        # Revisa si algún corte debería ejecutarse HOY por día de aviso (dias_antes_gestion)
        dias_antes = 2
        try:
            from preventiva.infrastructure.persistence.repositories.parametros_repository import (
                SqlAlchemyParametrosRepository,
            )
            params_repo = SqlAlchemyParametrosRepository(sf)
            dias_antes = params_repo.obtener_int("dias_antes_gestion", 2)
        except Exception:
            pass

        for corte in dias_corte:
            # Calcula la fecha real del corte este mes
            import calendar
            ultimo = calendar.monthrange(hoy.year, hoy.month)[1]
            dia_real = min(corte, ultimo)
            from datetime import timedelta
            fecha_corte_mes = date(hoy.year, hoy.month, dia_real)
            fecha_inicio_gestion = fecha_corte_mes - timedelta(days=dias_antes)
            if hoy == fecha_inicio_gestion:
                return corte

    except Exception as exc:
        log.warning("No se pudo determinar dia_corte desde BD: %s", exc)

    return None


def _ejecutar_job(cfg: PreventivaSettings) -> None:
    """Función que APScheduler llama en cada disparo del cron."""
    hoy = date.today()
    log.info("=== Scheduler disparado: %s ===", hoy.isoformat())

    dia_corte = _resolver_dia_corte(cfg, hoy)

    if dia_corte is None:
        log.info("Sin corte activo para %s — se omite ejecución.", hoy)
        return

    modo = "corte" if cfg.prev_ejecucion_corte else "diario"
    log.info("Ejecutando pipeline  fecha=%s  corte=%s  modo=%s", hoy, dia_corte, modo)

    from preventiva.jobs.preventiva_runner import ejecutar_preventiva

    ctx = ejecutar_preventiva(
        fecha_ejecucion=hoy,
        dia_corte=dia_corte,
        modo=modo,
        settings=cfg,
    )

    if ctx.ok:
        log.info(
            "Pipeline OK — proceso=%s  seleccionados=%d  isabel=%s",
            ctx.proceso_cod, len(ctx.seleccionados), ctx.ruta_isabel,
        )
    else:
        log.error("Pipeline ERROR — proceso=%s  motivo=%s", ctx.proceso_cod, ctx.mensaje_error)


def iniciar_scheduler(cfg: Optional[PreventivaSettings] = None) -> None:
    """
    Arranca el BlockingScheduler. Bloquea hasta SIGINT/SIGTERM.

    Configuración (leída del .env):
      PREV_SCHEDULER_HORA=6       → hora de disparo
      PREV_SCHEDULER_MINUTO=30    → minuto de disparo
      PREV_SCHEDULER_TZ=America/Guayaquil
      PREV_SCHEDULER_DIAS=mon,tue,wed,thu,fri
    """
    cfg = cfg or PreventivaSettings()

    scheduler = BlockingScheduler(timezone=cfg.prev_scheduler_tz)

    trigger = CronTrigger(
        day_of_week=cfg.prev_scheduler_dias,
        hour=cfg.prev_scheduler_hora,
        minute=cfg.prev_scheduler_minuto,
        timezone=cfg.prev_scheduler_tz,
    )

    scheduler.add_job(
        _ejecutar_job,
        trigger=trigger,
        args=[cfg],
        id="preventiva_diaria",
        name="Gestión Preventiva — pipeline diario",
        max_instances=1,           # no solapar ejecuciones
        misfire_grace_time=300,    # tolera hasta 5 min de retraso del OS
    )

    log.info(
        "Scheduler iniciado  horario=%s:%02d  días=%s  tz=%s",
        cfg.prev_scheduler_hora,
        cfg.prev_scheduler_minuto,
        cfg.prev_scheduler_dias,
        cfg.prev_scheduler_tz,
    )

    def _detener(signum, frame):  # noqa: ARG001
        log.info("Señal %s recibida — deteniendo scheduler…", signum)
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _detener)
    signal.signal(signal.SIGTERM, _detener)

    scheduler.start()
