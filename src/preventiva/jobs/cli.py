"""CLI de gestión preventiva (comando: preventiva)."""

import logging
import sys
from datetime import date, datetime
from typing import Optional

import click

from preventiva.infrastructure.config.settings import PreventivaSettings


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


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
