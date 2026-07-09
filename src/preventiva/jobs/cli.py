"""CLI de gestión preventiva (comando: preventiva)."""

import logging
import sys
from datetime import date, datetime, timedelta
import calendar
from typing import Optional

import click

from preventiva.infrastructure.config.settings import PreventivaSettings


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _restar_meses(d: date, meses: int) -> date:
    """Resta N meses a una fecha manteniendo el día (ajusta en meses cortos)."""
    anio, mes, dia = d.year, d.month - meses, d.day
    while mes <= 0:
        mes += 12
        anio -= 1
    ultimo = calendar.monthrange(anio, mes)[1]
    return date(anio, mes, min(dia, ultimo))


@click.group()
def main() -> None:
    """Bot de Gestión Preventiva — EPICA GRC-03."""


@main.command("ejecutar")
@click.option("--fecha", default=None, help="Fecha DDMMAAAA (defecto: hoy)")
@click.option("--corte", default=None, type=int, help="Día de corte (ej. 15)")
@click.option("--modo", default="corte", type=click.Choice(["corte", "diario", "manual"]))
def ejecutar(fecha: Optional[str], corte: Optional[int], modo: str) -> None:
    """Ejecuta el pipeline de gestión preventiva."""
    cfg = PreventivaSettings()
    _setup_logging(cfg.log_level)

    fecha_dt: Optional[date] = None
    if fecha:
        try:
            fecha_dt = datetime.strptime(fecha, "%d%m%Y").date()
        except ValueError:
            click.echo(f"Fecha inválida: {fecha}. Usa DDMMAAAA.", err=True)
            sys.exit(1)

    from preventiva.jobs.preventiva_runner import ejecutar_preventiva

    ctx = ejecutar_preventiva(
        fecha_ejecucion=fecha_dt,
        dia_corte=corte,
        modo=modo,
        settings=cfg,
    )

    if ctx.ok:
        click.echo(
            f"[OK] Proceso {ctx.proceso_cod} — "
            f"{len(ctx.seleccionados)} gestiones — "
            f"Isabel: {ctx.ruta_isabel} — Reporte: {ctx.ruta_reporte}"
        )
    else:
        click.echo(f"[ERROR] {ctx.mensaje_error}", err=True)
        sys.exit(1)


@main.command("cargar-historico")
@click.option(
    "--meses", default=6, show_default=True, type=int,
    help="Meses hacia atrás desde hoy para buscar archivos CAMOROSICO.",
)
@click.option(
    "--desde", default=None,
    help="Fecha inicio DDMMAAAA (sobreescribe --meses).",
)
@click.option(
    "--hasta", default=None,
    help="Fecha fin DDMMAAAA (defecto: ayer).",
)
@click.option(
    "--forzar", is_flag=True, default=False,
    help="Re-carga fechas que ya tienen registros en historial_mora_detalle.",
)
@click.option(
    "--log-level", default="INFO", show_default=True,
    help="Nivel de log: DEBUG|INFO|WARNING.",
)
def cargar_historico(
    meses: int,
    desde: Optional[str],
    hasta: Optional[str],
    forzar: bool,
    log_level: str,
) -> None:
    """
    Carga en historial_mora_detalle los archivos CAMOROSICO del pasado.

    \b
    Cuándo usarlo:
      - Primera puesta en producción (la tabla está vacía).
      - Después de una interrupción prolongada (varios días sin correr el job).

    \b
    Flujo del scheduler diario (recordatorio):
      1. El job corre cada día en el horario configurado.
      2. ParseLisHandler lee el CAMOROSICO de HOY.
      3. HistorialMoraHandler guarda esos registros y consulta el promedio
         de los últimos N meses (mismo día N-1 meses atrás … hoy).
      4. El backfill garantiza que esa ventana ya tenga datos al arrancarse.
    """
    cfg = PreventivaSettings()
    _setup_logging(log_level)
    log = logging.getLogger("preventiva.cli.backfill")

    hoy = date.today()
    ayer = hoy - timedelta(days=1)

    # Rango de fechas
    if desde:
        try:
            fecha_ini = datetime.strptime(desde, "%d%m%Y").date()
        except ValueError:
            click.echo(f"Fecha --desde inválida: {desde}. Usa DDMMAAAA.", err=True)
            sys.exit(1)
    else:
        fecha_ini = _restar_meses(hoy, meses - 1)   # mismo cálculo que HistorialMoraHandler

    if hasta:
        try:
            fecha_fin = datetime.strptime(hasta, "%d%m%Y").date()
        except ValueError:
            click.echo(f"Fecha --hasta inválida: {hasta}. Usa DDMMAAAA.", err=True)
            sys.exit(1)
    else:
        fecha_fin = ayer   # hasta ayer; hoy lo carga el job normal

    if fecha_ini > fecha_fin:
        click.echo(f"Rango vacío: {fecha_ini} > {fecha_fin}", err=True)
        sys.exit(1)

    click.echo(f"Backfill CAMOROSICO: {fecha_ini} → {fecha_fin}  (forzar={forzar})")

    # Construir dependencias mínimas
    from pathlib import Path
    from cobranzas.infrastructure.persistence.session import get_session_factory
    from preventiva.infrastructure.config.lis_resolver import LisResolver
    from preventiva.infrastructure.persistence.database import (
        create_engine_preventiva, init_database,
    )
    from preventiva.infrastructure.persistence.repositories.historial_mora_repository import (
        SqlAlchemyHistorialMoraRepository,
    )
    from preventiva.infrastructure.persistence.repositories.parametros_repository import (
        SqlAlchemyParametrosRepository,
    )
    from preventiva.infrastructure.adapters.lis_camorosico_reader import leer_camorosico

    engine = create_engine_preventiva(cfg.database_url, echo=False)
    init_database(engine)
    sf = get_session_factory(engine)

    params_repo = SqlAlchemyParametrosRepository(sf)
    pat_camo    = params_repo.obtener("CAMOROSICO_LIS", "")

    lis_resolver = LisResolver(
        base_lis=Path(cfg.prev_origen_lis),
        patrones_camorosico=[pat_camo] if pat_camo else None,
    )
    mora_repo = SqlAlchemyHistorialMoraRepository(sf)

    total_dias   = (fecha_fin - fecha_ini).days + 1
    cargados     = 0
    omitidos     = 0
    sin_archivo  = 0

    fecha_actual = fecha_ini
    while fecha_actual <= fecha_fin:
        # Verificar si ya existen registros para esta fecha
        if not forzar and mora_repo.contar_por_fecha(fecha_actual) > 0:
            log.debug("Omitiendo %s (ya tiene datos)", fecha_actual)
            omitidos += 1
            fecha_actual += timedelta(days=1)
            continue

        archivos = lis_resolver.camorosico(fecha_actual)
        if not archivos:
            log.debug("Sin archivo CAMOROSICO para %s — omitido", fecha_actual)
            sin_archivo += 1
            fecha_actual += timedelta(days=1)
            continue

        registros = leer_camorosico(archivos[0], fecha_corte=fecha_actual)
        if registros:
            proceso_cod = f"BACKFILL_{fecha_actual.strftime('%Y%m%d')}"
            guardados = mora_repo.guardar_lote(registros, proceso_cod)
            click.echo(
                f"  {fecha_actual}  {archivos[0].name:<40}  {guardados:>5} registros"
            )
            cargados += guardados
        else:
            log.warning("Archivo vacío o sin cabecera: %s", archivos[0])
            sin_archivo += 1

        fecha_actual += timedelta(days=1)

    click.echo(
        f"\nResumen: {total_dias} días evaluados — "
        f"{cargados} registros cargados — "
        f"{omitidos} días omitidos (ya tenían datos) — "
        f"{sin_archivo} días sin archivo"
    )


@main.command("scheduler")
@click.option(
    "--hora", default=None, type=int,
    help="Sobreescribe PREV_SCHEDULER_HORA del .env (0-23).",
)
@click.option(
    "--minuto", default=None, type=int,
    help="Sobreescribe PREV_SCHEDULER_MINUTO del .env (0-59).",
)
@click.option(
    "--tz", default=None,
    help="Sobreescribe PREV_SCHEDULER_TZ del .env (p.ej. America/Guayaquil).",
)
@click.option(
    "--dias", default=None,
    help="Sobreescribe PREV_SCHEDULER_DIAS del .env (p.ej. mon,tue,wed,thu,fri).",
)
@click.option(
    "--log-level", default=None,
    help="Nivel de log (DEBUG|INFO|WARNING). Defecto: LOG_LEVEL del .env.",
)
def scheduler(
    hora: Optional[int],
    minuto: Optional[int],
    tz: Optional[str],
    dias: Optional[str],
    log_level: Optional[str],
) -> None:
    """
    Arranca el scheduler automático de gestión preventiva.

    \b
    Configuración en .env:
      PREV_SCHEDULER_HORA=6              ← hora de disparo (0-23)
      PREV_SCHEDULER_MINUTO=30           ← minuto de disparo (0-59)
      PREV_SCHEDULER_TZ=America/Guayaquil
      PREV_SCHEDULER_DIAS=mon,tue,wed,thu,fri

    Los parámetros de línea de comandos sobreescriben el .env temporalmente.
    El proceso se mantiene corriendo hasta recibir Ctrl+C o SIGTERM.
    """
    cfg = PreventivaSettings()

    # Sobreescritura puntual desde CLI (sin tocar el .env)
    if hora is not None:
        cfg.prev_scheduler_hora = hora
    if minuto is not None:
        cfg.prev_scheduler_minuto = minuto
    if tz is not None:
        cfg.prev_scheduler_tz = tz
    if dias is not None:
        cfg.prev_scheduler_dias = dias

    _setup_logging(log_level or cfg.log_level)

    click.echo(
        f"Scheduler preventiva — {cfg.prev_scheduler_hora:02d}:{cfg.prev_scheduler_minuto:02d} "
        f"[{cfg.prev_scheduler_dias}]  tz={cfg.prev_scheduler_tz}"
    )

    from preventiva.jobs.scheduler import iniciar_scheduler
    iniciar_scheduler(cfg)


@main.command("api")
@click.option("--host", default=None)
@click.option("--port", default=None, type=int)
def api(host: Optional[str], port: Optional[int]) -> None:
    """Inicia la API REST de gestión preventiva en :8001."""
    import uvicorn
    from preventiva.api.app import create_app

    cfg = PreventivaSettings()
    _setup_logging(cfg.log_level)
    app = create_app(cfg)
    uvicorn.run(
        app,
        host=host or cfg.prev_api_host,
        port=port or cfg.prev_api_port,
    )
