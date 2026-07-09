"""
Scheduler de Gestión Preventiva — lógica según HU líneas 28-52.

Regla (HU):
  El sistema genera el archivo de gestión preventiva con DOS (2) días de
  anticipación a la fecha de pago del socio, incluyendo el propio día de pago.
  → 3 ejecuciones por corte: (corte - 2), (corte - 1), (corte)

  Si la fecha de pago cae en sábado, domingo o feriado, se traslada al
  siguiente día hábil y las gestiones previas se ajustan en consecuencia.

Configuración (.env):
  PREV_SCHEDULER_HORA=6     ← hora de arranque del job diario (0-23)
  PREV_SCHEDULER_MINUTO=30  ← minuto de arranque (0-59)
  PREV_SCHEDULER_TZ=America/Guayaquil

  El scheduler corre todos los días a esa hora.
  Decide INTERNAMENTE si hoy corresponde ejecutar consultando los cortes
  activos en dbo.catalogo (clave prev_dias_corte) y los feriados en
  dbo.claves/dbo.catalogo.  No hay otra configuración de días.

Ejecución manual:
  Solo a través de la API REST (POST /ejecutar-preventiva) o CLI
  (preventiva ejecutar --fecha DDMMAAAA).
"""

import calendar
import logging
import signal
import sys
from datetime import date, timedelta
from typing import List, Optional, Set, Tuple

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from preventiva.infrastructure.config.settings import PreventivaSettings

log = logging.getLogger("preventiva.scheduler")


# ---------------------------------------------------------------------------
# Lógica HU: calcular días de ejecución para un corte dado
# ---------------------------------------------------------------------------

def _siguiente_dia_habil(d: date, feriados: Set[date]) -> date:
    """Avanza hasta el próximo día hábil (lunes-viernes, no feriado)."""
    siguiente = d + timedelta(days=1)
    while siguiente.weekday() >= 5 or siguiente in feriados:
        siguiente += timedelta(days=1)
    return siguiente


def _fecha_pago_efectiva(anio: int, mes: int, dia_corte: int, feriados: Set[date]) -> date:
    """
    Calcula la fecha real de pago para un corte en un mes dado.
    Si el día cae en fin de semana o feriado, avanza al siguiente hábil.
    """
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    dia_real = min(dia_corte, ultimo_dia)
    fecha = date(anio, mes, dia_real)
    if fecha.weekday() >= 5 or fecha in feriados:
        fecha = _siguiente_dia_habil(fecha, feriados)
    return fecha


def _dias_habiles_anteriores(fecha_pago: date, n: int, feriados: Set[date]) -> List[date]:
    """
    Retorna los N días hábiles inmediatamente anteriores a fecha_pago
    (sin incluir fecha_pago). Orden: más antiguo primero.
    """
    habiles: List[date] = []
    cursor = fecha_pago - timedelta(days=1)
    while len(habiles) < n:
        if cursor.weekday() < 5 and cursor not in feriados:
            habiles.append(cursor)
        cursor -= timedelta(days=1)
    return list(reversed(habiles))


def _calcular_dias_ejecucion(
    hoy: date,
    dias_corte: Set[int],
    feriados: Set[date],
    dias_antes: int = 2,
) -> List[Tuple[date, int]]:
    """
    Para el mes de hoy (y el mes siguiente si aplica), calcula todos los
    días en que debe ejecutarse el pipeline.

    Retorna lista de (fecha_ejecucion, dia_corte) donde fecha_ejecucion == hoy.
    """
    resultado: List[Tuple[date, int]] = []

    # Evalúa mes actual y el anterior (para cortes que caen a principios de mes
    # pero cuyas gestiones previas empezaron el mes anterior)
    for delta_mes in (-1, 0, 1):
        mes = hoy.month + delta_mes
        anio = hoy.year
        if mes < 1:
            mes += 12
            anio -= 1
        elif mes > 12:
            mes -= 12
            anio += 1

        for corte in dias_corte:
            fecha_pago = _fecha_pago_efectiva(anio, mes, corte, feriados)
            # Días de gestión: los N días hábiles anteriores + el propio día de pago
            dias_gestion = _dias_habiles_anteriores(fecha_pago, dias_antes, feriados)
            dias_gestion.append(fecha_pago)

            if hoy in dias_gestion:
                resultado.append((hoy, corte))

    return resultado


# ---------------------------------------------------------------------------
# Carga de datos desde BD
# ---------------------------------------------------------------------------

def _cargar_dias_corte(sf) -> Set[int]:
    """Lee los días de corte activos desde dbo.catalogo (clave prev_dias_corte)."""
    try:
        from sqlalchemy import text
        with sf() as session:
            filas = session.execute(
                text(
                    "SELECT c.valor FROM dbo.catalogo c "
                    "JOIN dbo.claves k ON k.id_clave = c.id_clave "
                    "WHERE k.clave = 'prev_dias_corte' AND c.vigencia = 1"
                )
            ).fetchall()
        dias: Set[int] = set()
        for fila in filas:
            for parte in str(fila[0]).split(","):
                parte = parte.strip()
                if parte.isdigit():
                    dias.add(int(parte))
        return dias
    except Exception as exc:
        log.warning("No se pudieron leer dias_corte: %s", exc)
        return set()


def _cargar_feriados(sf, clave_feriados: str) -> Set[date]:
    """Lee feriados vigentes desde dbo.claves/dbo.catalogo."""
    try:
        from cobranzas.infrastructure.persistence.repositories.feriados_calendario_repository import (
            SqlAlchemyFeriadosCalendarioRepository,
        )
        repo = SqlAlchemyFeriadosCalendarioRepository(sf, clave_feriados)
        return repo.fechas_vigentes()
    except Exception as exc:
        log.warning("No se pudieron cargar feriados: %s", exc)
        return set()


# ---------------------------------------------------------------------------
# Job principal
# ---------------------------------------------------------------------------

def _ejecutar_job(cfg: PreventivaSettings) -> None:
    """Función que APScheduler llama cada día a la hora configurada."""
    from cobranzas.infrastructure.persistence.session import get_session_factory
    from preventiva.infrastructure.persistence.database import create_engine_preventiva
    from preventiva.infrastructure.persistence.repositories.parametros_repository import (
        SqlAlchemyParametrosRepository,
    )

    hoy = date.today()
    log.info("=== Scheduler preventiva: %s ===", hoy.isoformat())

    engine = create_engine_preventiva(cfg.database_url, echo=False)
    sf = get_session_factory(engine)

    params_repo = SqlAlchemyParametrosRepository(sf)
    dias_antes  = params_repo.obtener_int("dias_antes_gestion", cfg.prev_dias_antes_gestion)

    dias_corte = _cargar_dias_corte(sf)
    if not dias_corte:
        log.warning("Sin días de corte configurados en dbo.catalogo — se omite ejecución.")
        return

    feriados = _cargar_feriados(sf, cfg.clave_feriados)

    ejecuciones = _calcular_dias_ejecucion(hoy, dias_corte, feriados, dias_antes)

    if not ejecuciones:
        log.info("Hoy (%s) no corresponde a ningún día de gestión preventiva.", hoy)
        return

    from preventiva.jobs.preventiva_runner import ejecutar_preventiva

    for _, corte in ejecuciones:
        log.info("Ejecutando pipeline  fecha=%s  corte=%s", hoy, corte)
        ctx = ejecutar_preventiva(
            fecha_ejecucion=hoy,
            dia_corte=corte,
            modo="corte",
            settings=cfg,
        )
        if ctx.ok:
            log.info(
                "OK  proceso=%s  seleccionados=%d  gestión=%d",
                ctx.proceso_cod, len(ctx.seleccionados), ctx.numero_gestion,
            )
        else:
            log.error("ERROR  proceso=%s  motivo=%s", ctx.proceso_cod, ctx.mensaje_error)


# ---------------------------------------------------------------------------
# Arranque del scheduler
# ---------------------------------------------------------------------------

def iniciar_scheduler(cfg: Optional[PreventivaSettings] = None) -> None:
    """
    Arranca el BlockingScheduler. Bloquea hasta SIGINT/SIGTERM.

    Corre todos los días a PREV_SCHEDULER_HORA:PREV_SCHEDULER_MINUTO.
    La decisión de ejecutar o no el pipeline la toma la lógica HU interna.
    """
    cfg = cfg or PreventivaSettings()

    scheduler = BlockingScheduler(timezone=cfg.prev_scheduler_tz)

    # Corre TODOS los días — la lógica interna filtra si corresponde ejecutar
    trigger = CronTrigger(
        day_of_week="mon,tue,wed,thu,fri,sat,sun",
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
        max_instances=1,
        misfire_grace_time=300,
    )

    log.info(
        "Scheduler iniciado  arranque=%02d:%02d  tz=%s  "
        "| lógica de ejecución según HU (2 días antes del corte + día de corte)",
        cfg.prev_scheduler_hora,
        cfg.prev_scheduler_minuto,
        cfg.prev_scheduler_tz,
    )

    def _detener(signum, frame):  # noqa: ARG001
        log.info("Señal %s recibida — deteniendo scheduler…", signum)
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _detener)
    signal.signal(signal.SIGTERM, _detener)

    scheduler.start()
